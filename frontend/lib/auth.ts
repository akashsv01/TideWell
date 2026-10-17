// Sign-in is optional. It turns on only when Clerk keys are set (frontend/.env.local), so the app
// still runs for anyone without a Clerk account, and Clerk never auto-creates a temporary
// ("keyless") app on someone's behalf.
export const AUTH_ENABLED = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
