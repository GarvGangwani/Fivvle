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
  type User,
} from "firebase/auth";
import { FirebaseError } from "firebase/app";
import { getFirebaseAuth } from "./firebase";
import { syncUser } from "./api";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  isAdmin: boolean;
  refreshProfile: () => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  logOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
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
          await syncAppUser(credential.user);
        }
      } catch {
        /* surfaced via auth state / login UI if needed */
      }
    }

    void handleRedirectResult();

    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        void syncAppUser(firebaseUser).finally(() => {
          if (!cancelled) setLoading(false);
        });
      } else {
        setIsAdmin(false);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, []);

  async function signUp(email: string, password: string): Promise<void> {
    const auth = getFirebaseAuth();
    const credential = await createUserWithEmailAndPassword(
      auth,
      email,
      password,
    );
    await syncAppUser(credential.user);
  }

  async function signIn(email: string, password: string): Promise<void> {
    const auth = getFirebaseAuth();
    const credential = await signInWithEmailAndPassword(auth, email, password);
    await syncAppUser(credential.user);
  }

  async function signInWithGoogle(): Promise<void> {
    const auth = getFirebaseAuth();
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });

    try {
      const credential = await signInWithPopup(auth, provider);
      await syncAppUser(credential.user);
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

  return (
    <AuthContext.Provider
      value={{
        user,
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
