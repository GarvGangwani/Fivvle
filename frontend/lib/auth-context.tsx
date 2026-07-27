"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  GoogleAuthProvider,
  signOut,
  updateProfile,
  type User,
} from "firebase/auth";
import { FirebaseError } from "firebase/app";
import { getFirebaseAuth } from "./firebase";
import { syncUser } from "./api";

export type AuthStatus =
  | "initializing"
  | "authenticated"
  | "unauthenticated";

type AuthContextValue = {
  user: User | null;
  /** Firebase session resolve state. Prefer this over inferring from `user`. */
  status: AuthStatus;
  /** True while `status === "initializing"`. */
  loading: boolean;
  isAdmin: boolean;
  refreshProfile: () => Promise<void>;
  signUp: (
    email: string,
    password: string,
    displayName?: string,
  ) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  logOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("initializing");
  const [isAdmin, setIsAdmin] = useState(false);

  async function syncAppUser(firebaseUser: User): Promise<void> {
    try {
      const profile = await syncUser(firebaseUser);
      setIsAdmin(profile.is_admin);
    } catch {
      setIsAdmin(false);
    }
  }

  async function refreshProfile(): Promise<void> {
    const auth = getFirebaseAuth();
    const firebaseUser = auth.currentUser;
    if (!firebaseUser) {
      setIsAdmin(false);
      return;
    }
    await syncAppUser(firebaseUser);
  }

  useEffect(() => {
    const auth = getFirebaseAuth();
    let cancelled = false;

    async function handleRedirectResult() {
      try {
        const credential = await getRedirectResult(auth);
        if (credential?.user && !cancelled) {
          setUser(credential.user);
          await syncAppUser(credential.user);
          if (!cancelled) setStatus("authenticated");
        }
      } catch {
        /* surfaced via auth state / login UI if needed */
      }
    }

    void handleRedirectResult();

    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      if (firebaseUser) {
        setUser(firebaseUser);
        void syncAppUser(firebaseUser).finally(() => {
          if (!cancelled) setStatus("authenticated");
        });
      } else {
        setUser(null);
        setIsAdmin(false);
        setStatus("unauthenticated");
      }
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, []);

  async function signUp(
    email: string,
    password: string,
    displayName?: string,
  ): Promise<void> {
    const auth = getFirebaseAuth();
    const credential = await createUserWithEmailAndPassword(
      auth,
      email,
      password,
    );
    const trimmed = displayName?.trim();
    if (trimmed) {
      await updateProfile(credential.user, { displayName: trimmed });
    }
    setUser(credential.user);
    await syncAppUser(credential.user);
    setStatus("authenticated");
  }

  async function signIn(email: string, password: string): Promise<void> {
    const auth = getFirebaseAuth();
    const credential = await signInWithEmailAndPassword(auth, email, password);
    setUser(credential.user);
    await syncAppUser(credential.user);
    setStatus("authenticated");
  }

  async function signInWithGoogle(): Promise<void> {
    const auth = getFirebaseAuth();
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });

    try {
      const credential = await signInWithPopup(auth, provider);
      setUser(credential.user);
      await syncAppUser(credential.user);
      setStatus("authenticated");
    } catch (err) {
      const shouldRedirect =
        err instanceof FirebaseError &&
        (err.code === "auth/popup-blocked" ||
          err.code === "auth/internal-error" ||
          err.code === "auth/cancelled-popup-request");

      if (shouldRedirect) {
        await signInWithRedirect(auth, provider);
        return;
      }
      throw err;
    }
  }

  async function logOut(): Promise<void> {
    const auth = getFirebaseAuth();
    setIsAdmin(false);
    await signOut(auth);
  }

  const loading = status === "initializing";

  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        loading,
        isAdmin,
        refreshProfile,
        signUp,
        signIn,
        signInWithGoogle,
        logOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

/** Returns null when rendered outside AuthProvider (e.g. marketing pages). */
export function useOptionalAuth(): AuthContextValue | null {
  return useContext(AuthContext);
}
