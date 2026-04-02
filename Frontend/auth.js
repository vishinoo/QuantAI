/**
 * auth.js — QuantAI Firebase Authentication
 *
 * Handles:
 *  1. Google Sign-In popup
 *  2. Session persistence (Firebase handles this automatically)
 *  3. Exposing user ID + auth token for API calls
 *  4. Notifying the rest of the app on auth state changes
 *
 * SETUP:
 *  1. Go to https://console.firebase.google.com
 *  2. Create a project → Enable Google Authentication
 *  3. Add your domain to "Authorised domains"
 *  4. Replace the firebaseConfig object below with your project's config
 */

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.0/firebase-app.js";
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  signOut,
  onAuthStateChanged,
} from "https://www.gstatic.com/firebasejs/10.12.0/firebase-auth.js";

/* ─────────────────────────────────────────
   🔧 REPLACE WITH YOUR FIREBASE CONFIG
   (Firebase console → Project settings → Your apps)
───────────────────────────────────────── */
const firebaseConfig = {
  apiKey:            "YOUR_API_KEY",
  authDomain:        "YOUR_PROJECT_ID.firebaseapp.com",
  projectId:         "YOUR_PROJECT_ID",
  storageBucket:     "YOUR_PROJECT_ID.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId:             "YOUR_APP_ID",
};

/* ─────────────────────────────────────────
   INITIALISE FIREBASE
───────────────────────────────────────── */
const firebaseApp = initializeApp(firebaseConfig);
const auth        = getAuth(firebaseApp);
const provider    = new GoogleAuthProvider();

// Request additional scopes if needed
provider.addScope("profile");
provider.addScope("email");

/* ─────────────────────────────────────────
   PUBLIC API  (consumed by app.js and api.js)
───────────────────────────────────────── */

/**
 * Open the Google sign-in popup.
 * On success the onAuthStateChanged listener fires automatically.
 */
export async function loginWithGoogle() {
  try {
    await signInWithPopup(auth, provider);
    // Auth state change is handled by onAuthStateChanged below
  } catch (err) {
    if (err.code !== "auth/popup-closed-by-user") {
      console.error("Login failed:", err);
      alert("Login failed. Please try again.");
    }
  }
}

/**
 * Sign the current user out.
 */
export async function logout() {
  await signOut(auth);
}

/**
 * Get the current Firebase ID token (used by api.js for every request).
 * Returns null if no user is signed in.
 */
export async function getToken() {
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken(/* forceRefresh */ false);
}

/**
 * Return the current user object synchronously.
 * Returns null if not logged in.
 */
export function getCurrentUser() {
  return auth.currentUser;
}

/**
 * Return basic profile info for the logged-in user.
 * Returns null if not logged in.
 */
export function getUserProfile() {
  const user = auth.currentUser;
  if (!user) return null;
  return {
    uid:         user.uid,
    name:        user.displayName,
    email:       user.email,
    photoURL:    user.photoURL,
  };
}

/**
 * Register a callback that fires whenever auth state changes.
 * Callback receives the Firebase user object (or null on logout).
 * Returns an unsubscribe function.
 *
 * Usage:
 *   import { onAuth } from './auth.js';
 *   const unsub = onAuth(user => { ... });
 */
export function onAuth(callback) {
  return onAuthStateChanged(auth, callback);
}

/* ─────────────────────────────────────────
   Expose to window so non-module HTML
   onclick="window.auth.loginWithGoogle()" works
───────────────────────────────────────── */
window.auth = { loginWithGoogle, logout };
