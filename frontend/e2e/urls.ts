// Test-only addresses; application ports and API configuration are unaffected.
export const testBackendUrl = `http://127.0.0.1:${process.env.MOTOR_E2E_BACKEND_PORT || 18001}`;
export const testFrontendUrl = `http://127.0.0.1:${process.env.MOTOR_E2E_FRONTEND_PORT || 15173}`;
