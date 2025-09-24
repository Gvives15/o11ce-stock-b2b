import axios from 'axios';

// Crear instancia de axios con configuración base
const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 15000, // 15 segundos como especificado
  withCredentials: false, // Configurado como false según especificación
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

// Interceptor para requests - agregar token si existe
axiosClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Log para debugging (solo en desarrollo)
    if (import.meta.env.DEV) {
      console.log(`🚀 ${config.method?.toUpperCase()} ${config.url}`, {
        headers: config.headers,
        data: config.data
      });
    }
    
    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

// Interceptor para responses - manejar errores de autenticación
axiosClient.interceptors.response.use(
  (response) => {
    // Log para debugging (solo en desarrollo)
    if (import.meta.env.DEV) {
      console.log(`✅ ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data);
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Log del error
    if (import.meta.env.DEV) {
      console.error(`❌ ${error.response?.status || 'Network'} Error:`, {
        url: originalRequest?.url,
        method: originalRequest?.method,
        message: error.message,
        response: error.response?.data
      });
    }

    // Manejar error 401 (no autorizado)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // Intentar renovar token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          console.log('🔄 Intentando renovar token...');
          const response = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/auth/refresh/`, {
            refresh: refreshToken
          });
          
          const { access } = response.data;
          localStorage.setItem('access_token', access);
          console.log('✅ Token renovado exitosamente');
          
          // Reintentar request original
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return axiosClient(originalRequest);
        } catch (refreshError) {
          console.error('❌ Error renovando token:', refreshError);
          // Si falla el refresh, limpiar tokens y redirigir a login
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          
          // Mostrar toast de error
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('auth-error', { 
              detail: { message: 'Sesión expirada. Por favor, inicia sesión nuevamente.' }
            }));
          }
          
          // Redirigir a login después de un breve delay
          setTimeout(() => {
            window.location.href = '/login';
          }, 1000);
        }
      } else {
        // No hay refresh token, limpiar y redirigir a login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        
        if (typeof window !== 'undefined') {
          window.dispatchEvent(new CustomEvent('auth-error', { 
            detail: { message: 'No hay sesión activa. Por favor, inicia sesión.' }
          }));
        }
        
        setTimeout(() => {
          window.location.href = '/login';
        }, 1000);
      }
    }

    // Manejar otros errores comunes
    if (error.response?.status >= 500) {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('server-error', { 
          detail: { message: 'Error del servidor. Por favor, intenta más tarde.' }
        }));
      }
    } else if (error.response?.status >= 400 && error.response?.status < 500) {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('client-error', { 
          detail: { 
            message: error.response?.data?.message || 'Error en la solicitud.',
            status: error.response?.status
          }
        }));
      }
    } else if (error.code === 'ECONNABORTED') {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('timeout-error', { 
          detail: { message: 'La solicitud tardó demasiado. Verifica tu conexión.' }
        }));
      }
    } else if (!error.response) {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('network-error', { 
          detail: { message: 'Error de conexión. Verifica tu red.' }
        }));
      }
    }

    return Promise.reject(error);
  }
);

export default axiosClient;
export { axiosClient };