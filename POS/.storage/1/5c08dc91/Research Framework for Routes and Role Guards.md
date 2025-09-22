# Research Framework

*   **Vue Router Navigation Guards for Authentication & Authorization:**
    *   **Knowledge to acquire:** Deep understanding of Vue Router's `beforeEach` navigation guard lifecycle, handling asynchronous operations (like fetching user profiles) within guards, and effectively defining and interpreting route `meta` fields for authentication (`requiresAuth`) and authorization (`roles`).
    *   **Evidence needed:** Official Vue Router documentation, widely adopted community patterns for secure and efficient guard implementations, and performance considerations when integrating API calls into navigation guards.
    *   **Topics for source-based searching:** Best practices for asynchronous `await` calls in `beforeEach` guards, strategies to prevent race conditions or unnecessary profile fetches, and implementing complex role-based access logic (e.g., handling `OR` conditions for roles).

*   **Pinia Store Management for User Authentication State:**
    *   **Knowledge to acquire:** Best practices for structuring a Pinia store to securely manage authentication-related state, including `tokenAccess`, `roles`, and a `profileLoaded` flag. Understanding Pinia's reactivity model and ensuring state consistency across the application.
    *   **Evidence needed:** Official Pinia documentation, common architectural patterns for authentication stores in large-scale Vue/Pinia applications, and considerations for initial state hydration and persistence (if applicable, though not strictly in scope).
    *   **Topics for source-based searching:** Ensuring reactive updates to UI elements based on authentication state changes, managing the initial `profileLoaded` state to avoid UI flickering, and robust error handling within store actions that interact with backend APIs.

*   **User Experience (UX) Considerations for Authentication Flows:**
    *   **Knowledge to acquire:** Principles for designing a smooth and intuitive user experience during authentication and authorization processes, including effective loading states, clear access denied messages, and seamless redirection mechanisms.
    *   **Evidence needed:** General UX/UI best practices for web applications, examples of well-implemented authentication flows in single-page applications, and guidelines for providing informative user feedback.
    *   **Topics for source-based searching:** Implementing global loading indicators beyond simple progress bars (e.g., custom overlays, skeleton loaders), secure methods for post-login redirection using query parameters, and designing an effective and user-friendly "Access Denied" view.

*   **Robust Error Handling and Edge Case Management:**
    *   **Knowledge to acquire:** Strategies for anticipating and gracefully handling various error conditions and edge cases that can arise during the authentication and authorization process, particularly concerning API call failures and invalid states.
    *   **Evidence needed:** Common pitfalls in client-side authentication, recommended error handling patterns in Vue.js and JavaScript, security implications of token expiration or invalid backend responses.
    *   **Topics for source-based searching:** Handling network errors or server-side failures during the `/auth/me` API call, implementing fallbacks for invalid or expired tokens (even before an interceptor is in place), and managing scenarios where backend returns unexpected or empty role data.

*   **Testing Strategies for Authentication Guards and Stores:**
    *   **Knowledge to acquire:** Effective methodologies for unit, integration, and end-to-end testing of Vue Router guards and Pinia authentication stores to ensure reliability and prevent regressions.
    *   **Evidence needed:** Jest/Vitest and Playwright/Cypress documentation for testing Vue components and router interactions, and examples of testing complex authentication and authorization flows in a modern Vue application.
    *   **Topics for source-based searching:** Techniques for mocking Vue Router and Pinia store states for isolated unit tests, simulating various user roles and authentication statuses in integration tests, and verifying correct redirection and access control in end-to-end scenarios.

# Search Plan

1.  **Vue Router `beforeEach` guard best practices for handling asynchronous user profile fetching (e.g., `await auth.loadProfile()`) and preventing UI flickering.**

2.  **Secure implementation guidelines for post-login redirects using query parameters (`?redirect=`) in Vue Router to avoid open redirect vulnerabilities.**

3.  **Modern global loading indicator patterns and alternatives to `NProgress` for Vue 3 applications during asynchronous navigation guard execution.**

4.  **Robust error handling strategies for `axios` API call failures within Pinia store actions and Vue Router guards, specifically triggering logout and redirection.**

5.  **Techniques to ensure the Pinia authentication store's `profileLoaded` state effectively prevents protected routes from rendering before user roles are fully available.**

6.  **Detailed examples for unit testing Vue Router `beforeEach` guards, including mocking Pinia store state and simulating asynchronous API responses for user roles.**