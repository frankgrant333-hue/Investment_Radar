# 📱 Phone access setup — Streamlit Community Cloud

Follow these steps in order. Each step has a checkpoint — reply to
Claude at each ✅ before moving to the next so we can catch problems
early.

**What we're doing:** hosting a read-only copy of your Investment
Radar dashboard on Streamlit's free servers, backed by a GitHub
repo. Once it's live, you'll be able to open it in mobile Chrome
from anywhere — work, coffee shop, wherever — and see your scored
watchlist without your Mac having to be on.

**What you need:** your Mac, an email address, and about 45 minutes.

---

## Step 1 — Create a GitHub account (10 min)

1. Go to https://github.com in your browser.
2. Click **Sign up** (top right).
3. Enter an email address. Use one you check — GitHub will send a
   verification code.
4. Create a password (strong — GitHub is where your code lives).
5. Pick a username. This becomes part of your public URL, so
   something like `frankgrant` or similar. **You cannot easily
   change this later.**
6. Complete the CAPTCHA and email verification.
7. When it asks about "How will you use GitHub?" pick "Just me"
   or similar. Skip the tour if offered.

**✅ Checkpoint:** you should now be logged into GitHub, looking
at a mostly-empty dashboard. Tell Claude your GitHub username so
subsequent instructions can reference it.

---

## Step 2 — Install GitHub Desktop (5 min)

GitHub Desktop is a free app that gives you a friendly GUI for
Git. It's way easier than command-line git for a beginner.

1. Go to https://desktop.github.com
2. Click **Download for macOS**.
3. Open the downloaded `.zip` if it doesn't auto-extract, then
   drag **GitHub Desktop** into your Applications folder.
4. Launch **GitHub Desktop** from Applications.
5. When it asks, sign in with your GitHub account from Step 1.
6. It'll ask about your name and email — use whatever you'd like
   attached to your commits. (First name + email is fine.)

**✅ Checkpoint:** GitHub Desktop is open, showing an empty
"Let's get started" screen or "No repositories" state.

---

## Step 3 — Create a new private repository (5 min)

1. In GitHub Desktop, click **File → New Repository...** (or use
   the "Create a New Repository on your hard drive" button).
2. Fill in:
   - **Name:** `Investment_Radar` (exactly — matches your folder)
   - **Description:** *Personal investment idea capture & ranking*
     (or whatever you'd like)
   - **Local Path:** click **Choose...** and navigate to your home
     folder. Pick your home folder (`/Users/frankgrant`).
     GitHub Desktop will detect that `Investment_Radar` already
     exists as a folder and offer to use it. **Say YES.** This is
     the moment your project files get "adopted" into the repo.
   - **Initialize this repository with a README:** **UNCHECK** this
     (we already have a README).
   - **Git Ignore:** leave as "None" (we already have `.gitignore`).
   - **License:** leave as "None".
3. Click **Create Repository**.

**✅ Checkpoint:** GitHub Desktop should now show your
Investment_Radar folder, with a long list of "changes" in the
left sidebar — every file we've built together.

---

## Step 4 — Publish to GitHub (5 min)

Right now the repo only exists locally. Let's push it to GitHub
so Streamlit Cloud can see it.

1. In GitHub Desktop, at the bottom of the "Changes" panel on the
   left, you'll see a **commit box** with two fields:
   - **Summary:** type `Initial commit`
   - **Description:** leave blank
2. Click the blue **Commit to main** button.
3. At the top of the window, click **Publish repository**.
4. In the dialog:
   - **Name:** `Investment_Radar` (should already be filled in)
   - **Description:** whatever you'd like
   - **✅ Keep this code private** — CHECK THIS BOX. Your ticker
     list is personal.
5. Click **Publish repository**.

**✅ Checkpoint:** open https://github.com in your browser, click
your profile picture → **Your repositories**. You should see
`Investment_Radar` at the top with a 🔒 (lock) icon showing it's
private. Click into it — you should see all the code files.

---

## Step 5 — Sign up for Streamlit Community Cloud (5 min)

1. Go to https://share.streamlit.io
2. Click **Sign up** (or "Continue with GitHub" if that's offered).
3. Authorize Streamlit to access your GitHub account. It'll ask
   for permissions to read your repositories — that's expected.
4. Fill in any onboarding fields (name, "how will you use it", etc.)

**✅ Checkpoint:** you land on the Streamlit Community Cloud
dashboard — probably empty or offering to create your first app.

---

## Step 6 — Deploy the app (5 min + wait ~2 min for build)

1. On the Streamlit Cloud dashboard, click **Create app** (or
   **New app**).
2. Choose **Deploy a public app from GitHub** or **Deploy from
   existing repo**.
3. Fill in:
   - **Repository:** `<your-username>/Investment_Radar`
     (should show in a dropdown once you type)
   - **Branch:** `main`
   - **Main file path:** `radar/app.py`
   - **App URL** (custom subdomain): pick something like
     `frank-investment-radar` — this becomes
     `frank-investment-radar.streamlit.app`
4. Click **Deploy!**

Streamlit will now clone your repo, install everything in
`requirements.txt` (pandas, yfinance, streamlit), and boot the
app. This takes 1–3 minutes. You'll see live build logs — mostly
`pip install ...` output. Wait for it to say "Your app is live!"

**✅ Checkpoint:** you should see the dashboard load in Streamlit
Cloud. Same layout as your Mac dashboard, BUT: the sidebar shows
"📱 Phone view — read only" instead of the Add-a-ticker form. No
Save button. No Snapshot button. No Edit toggle. That's expected —
that's the read-only phone view.

---

## Step 7 — Test on your phone (2 min)

1. On your iPhone, open **Chrome** (or Safari).
2. Visit `https://<your-app>.streamlit.app` (whatever URL you
   picked in Step 6).
3. It should load your radar. Try:
   - Tapping the filter expander
   - Expanding a ticker for the detail view
   - Sorting by different columns
4. To make it feel like an app: tap the **share** icon (Safari:
   the square-with-arrow-up; Chrome: the three-dot menu) → **Add
   to Home Screen**. Name it "Radar" or "Investment Radar". Now
   it lives as an icon on your home screen.

**✅ Checkpoint:** you can open your Radar from your phone's home
screen from anywhere with internet. Congratulations — you now
have a real hosted app.

---

## Step 8 — The daily sync-to-phone flow (going forward)

Every time you add or edit tickers on your Mac and want the phone
view updated:

1. Add/edit as usual in the Mac dashboard, hit **💾 Save changes**.
   (Your Mac now writes to both iCloud AND the local repo copy
   automatically — no manual copying required.)
2. Open **GitHub Desktop**. You'll see the changed `ideas.csv`
   file listed under "Changes".
3. In the commit box, type a short message like `Add MU` or
   `Update themes` and click **Commit to main**.
4. Click **Push origin** (top right).
5. Wait ~30-60 seconds. Streamlit Cloud detects the push and
   redeploys automatically. Refresh your phone browser — new data
   is there.

That's the whole loop.

---

## Troubleshooting

**"App failed to deploy"** — check the build logs on Streamlit
Cloud. Most likely a package version mismatch. Tell Claude the
exact error message.

**"App loads but shows an error about ideas.csv"** — the CSV
might not have been committed. In GitHub Desktop, check that
`ideas.csv` is not grayed-out in the changes panel. If it's not
there at all, run one save from your Mac dashboard first, then
commit + push.

**"Phone shows old data"** — you probably forgot to commit + push
after saving. Repeat Step 8.

**"App went to sleep"** — Streamlit Community Cloud puts unused
apps to sleep after ~7 days of inactivity. Just visit the URL
and wait ~30 seconds for it to wake up. No data is lost.
