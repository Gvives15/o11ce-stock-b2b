"""Celery tasks for notifications with fault tolerance."""
import logging
import socket
import smtplib
from typing import Optional
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from apps.core.metrics import increment_orders_placed

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(smtplib.SMTPException, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,  # Max 10 minutes
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=30,  # 30 seconds
    time_limit=60,  # 1 minute
)
def send_email_alert(
    self,
    subject: str,
    message: str,
    recipient_email: str,
    from_email: Optional[str] = None
):
    """
    Send email alert with automatic retries on SMTP failures.
    
    Args:
        subject: Email subject
        message: Email body
        recipient_email: Recipient email address
        from_email: Sender email (optional)
    """
    try:
        logger.info(f"Sending email alert to {recipient_email}: {subject}")
        
        # Use default from_email if not provided
        if not from_email:
            from_email = settings.DEFAULT_FROM_EMAIL
        
        # Send email with timeout
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[recipient_email],
            fail_silently=False,
            timeout=5  # 5 seconds timeout
        )
        
        logger.info(f"Email alert sent successfully to {recipient_email}")
        increment_counter('email_alerts_sent_total', {'status': 'success'})
        
        return {
            'status': 'success',
            'recipient': recipient_email,
            'subject': subject
        }
        
    except (smtplib.SMTPException, ConnectionError, TimeoutError) as exc:
        logger.warning(
            f"Email alert failed (attempt {self.request.retries + 1}): {exc}",
            extra={'recipient': recipient_email, 'subject': subject}
        )
        increment_counter('email_alerts_sent_total', {'status': 'retry'})
        
        # Let autoretry_for handle the retry
        raise exc
        
    except Exception as exc:
        logger.error(
            f"Unexpected error sending email alert: {exc}",
            extra={'recipient': recipient_email, 'subject': subject}
        )
        increment_counter('email_alerts_sent_total', {'status': 'failed'})
        
        # Don't retry for unexpected errors
        return {
            'status': 'failed',
            'error': str(exc),
            'recipient': recipient_email
        }


@shared_task(
    bind=True,
    autoretry_for=(smtplib.SMTPException, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,  # Max 5 minutes
    retry_jitter=True,
    max_retries=2,
    soft_time_limit=45,  # 45 seconds
    time_limit=90,  # 1.5 minutes
)
def notify_new_order(self, order_id: int):
    """
    Send notification for new order with automatic retries.
    
    Args:
        order_id: Order ID to notify about
    """
    try:
        logger.info(f"Processing new order notification for order {order_id}")
        
        # Get order with timeout protection
        try:
            order = Order.objects.select_related('customer').get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} not found for notification")
            increment_counter('order_notifications_total', {'status': 'not_found'})
            return {'status': 'failed', 'error': 'Order not found'}
        
        # Prepare notification content
        subject = f"Nueva Orden #{order.id} - {order.customer.name}"
        message = f"""
        Nueva orden recibida:
        
        Orden: #{order.id}
        Cliente: {order.customer.name}
        Email: {order.customer.email}
        Total: ${order.total}
        Estado: {order.get_status_display()}
        Fecha: {order.created_at.strftime('%Y-%m-%d %H:%M')}
        
        Revisar en el panel de administración.
        """
        
        # Get notification recipients
        admin_emails = list(
            User.objects.filter(
                is_staff=True, 
                is_active=True,
                email__isnull=False
            ).exclude(email='').values_list('email', flat=True)
        )
        
        if not admin_emails:
            logger.warning("No admin emails found for order notification")
            increment_counter('order_notifications_total', {'status': 'no_recipients'})
            return {'status': 'skipped', 'reason': 'No admin emails'}
        
        # Send notifications to all admins
        results = []
        for admin_email in admin_emails:
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_email],
                    fail_silently=False,
                    timeout=5  # 5 seconds timeout
                )
                results.append({'email': admin_email, 'status': 'sent'})
                
            except Exception as email_exc:
                logger.warning(f"Failed to send to {admin_email}: {email_exc}")
                results.append({'email': admin_email, 'status': 'failed', 'error': str(email_exc)})
        
        # Check if at least one email was sent
        sent_count = sum(1 for r in results if r['status'] == 'sent')
        
        if sent_count > 0:
            logger.info(f"Order notification sent to {sent_count}/{len(admin_emails)} admins")
            increment_counter('order_notifications_total', {'status': 'success'})
            
            return {
                'status': 'success',
                'order_id': order_id,
                'sent_to': sent_count,
                'total_recipients': len(admin_emails),
                'results': results
            }
        else:
            # All emails failed, trigger retry
            logger.error(f"All order notification emails failed for order {order_id}")
            increment_counter('order_notifications_total', {'status': 'all_failed'})
            raise ConnectionError("All notification emails failed")
            
    except (smtplib.SMTPException, ConnectionError, TimeoutError) as exc:
        logger.warning(
            f"Order notification failed (attempt {self.request.retries + 1}): {exc}",
            extra={'order_id': order_id}
        )
        increment_counter('order_notifications_total', {'status': 'retry'})
        
        # Let autoretry_for handle the retry
        raise exc
        
    except Exception as exc:
        logger.error(
            f"Unexpected error in order notification: {exc}",
            extra={'order_id': order_id}
        )
        increment_counter('order_notifications_total', {'status': 'failed'})
        
        return {
            'status': 'failed',
            'error': str(exc),
            'order_id': order_id
        }


@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=120,  # Max 2 minutes
    retry_jitter=True,
    max_retries=2,
    soft_time_limit=60,  # 1 minute
    time_limit=120,  # 2 minutes
)
def send_low_stock_alert(self, product_name: str, current_stock: float, min_stock: float):
    """
    Send low stock alert with automatic retries.
    
    Args:
        product_name: Name of the product
        current_stock: Current stock level
        min_stock: Minimum stock threshold
    """
    try:
        logger.info(f"Sending low stock alert for {product_name}")
        
        subject = f"⚠️ Stock Bajo: {product_name}"
        message = f"""
        ALERTA DE STOCK BAJO
        
        Producto: {product_name}
        Stock actual: {current_stock}
        Stock mínimo: {min_stock}
        
        Se recomienda reabastecer este producto.
        
        Revisar en el panel de stock.
        """
        
        # Get stock managers
        stock_managers = list(
            User.objects.filter(
                groups__name='Stock Managers',
                is_active=True,
                email__isnull=False
            ).exclude(email='').values_list('email', flat=True)
        )
        
        # Fallback to admins if no stock managers
        if not stock_managers:
            stock_managers = list(
                User.objects.filter(
                    is_staff=True,
                    is_active=True,
                    email__isnull=False
                ).exclude(email='').values_list('email', flat=True)
            )
        
        if not stock_managers:
            logger.warning("No recipients found for low stock alert")
            increment_counter('low_stock_alerts_total', {'status': 'no_recipients'})
            return {'status': 'skipped', 'reason': 'No recipients'}
        
        # Send alerts
        for manager_email in stock_managers:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[manager_email],
                fail_silently=False,
                timeout=5
            )
        
        logger.info(f"Low stock alert sent to {len(stock_managers)} managers")
        increment_counter('low_stock_alerts_total', {'status': 'success'})
        
        return {
            'status': 'success',
            'product': product_name,
            'sent_to': len(stock_managers)
        }
        
    except (smtplib.SMTPException, ConnectionError, TimeoutError) as exc:
        logger.warning(f"Low stock alert failed: {exc}")
        increment_counter('low_stock_alerts_total', {'status': 'retry'})
        raise exc
        
    except Exception as exc:
        logger.error(f"Unexpected error in low stock alert: {exc}")
        increment_counter('low_stock_alerts_total', {'status': 'failed'})
        
        return {
            'status': 'failed',
            'error': str(exc),
            'product': product_name
        }