import Wordmark from "@/components/Wordmark";
import AccountMenu from "@/components/AccountMenu";
import BottomNav, { TopNav } from "@/components/BottomNav";
import HealthAlertWatcher from "@/components/HealthAlertWatcher";
import RequirePatient from "@/components/RequirePatient";
import ThemeToggle from "@/components/ThemeToggle";

// Shared frame for the signed-in screens. One content width for every screen (max-w-3xl); the
// header carries the mark and, from md up, the section links. Phones get the tab bar instead.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col px-5 sm:px-8">
      <header>
        <div className="flex h-16 items-center justify-between gap-3 md:h-20">
          <Wordmark href="/home" />
          <div className="flex items-center gap-1 sm:gap-2">
            <ThemeToggle />
            <AccountMenu />
          </div>
        </div>
        <TopNav />
      </header>
      <main id="main" className="flex flex-1 flex-col pb-32 pt-4 md:pb-20 md:pt-10">
        <RequirePatient>{children}</RequirePatient>
      </main>
      <BottomNav />
      <HealthAlertWatcher />
    </div>
  );
}
