# DHAP Key Service — Setup Guide

## What this is, in plain words
The DHAP report can double-check a dealer's Google listing (**Google Places**) and the dealer's posts (**JEV**, from TypeSafe). Both need a secret password called an **API key**.

We don't want those keys on everyone's computer, and we can never put them on GitHub (it's public). So we keep both keys in **one safe place on Google Cloud**: a tiny program we call the **key service**. Everyone else gets only a **team code**. The team code lets them use the key service, and we can turn any team code off at any time.

```
Employee (Claude Code / Codex / Ask AI)  --team code-->  Key service on Google Cloud  --secret key-->  Google Places / JEV
```

**Who does what**
| Part | Who | How long | How often |
|---|---|---|---|
| A. Build the key service | The CTO (the person who owns the Google Cloud project) | About 15 minutes | Once |
| B. Set up a Mac for Claude Code and Codex | Each employee | About 5 minutes | Once per Mac |
| C. Set up Ask AI | The GoHighLevel (GHL) admin | About 5 minutes | Once |
| D. Everyday jobs | The CTO | 1 minute each | When needed |

**Words you'll see**
- **API key** — a secret password a program uses to talk to Google or TypeSafe.
- **Team code** — a password for *our* key service. It starts with `dhap_`. Each person gets their own.
- **Service address** — the web address of our key service. It starts with `https://`.
- **Cloud Shell** — a command window inside the Google Cloud website. Nothing to install.
- **Secret Manager** — Google Cloud's locked box for secrets. It holds the keys and everyone's team code. Each person can open only their own. (It costs a few cents a month, about $1 at most for a small team.)

> **Safety rules**
> 1. Never paste a key or a team code into email, Slack, a chat with an AI, or a document.
> 2. Never type them into a document. Each person reads their own code straight from Secret Manager (Part B shows how).
> 3. If you think one leaked, tell the CTO. The CTO can replace it in a minute (see Part D).

---

## Part A — Build the key service (CTO, one time)

### A1. Make a new Google Places key and lock it down
The old key was pasted into a chat, so we make a fresh one.
1. Go to **console.cloud.google.com** and sign in.
2. At the very top, click the **project picker** and choose the project that has the Places key.
3. In the left menu, click **APIs & Services**, then **Credentials**.
4. Click **+ Create credentials**, then **API key**. A new key appears. **Copy it** and keep the window open.
5. Click **Edit API key** (or click the key's name).
6. Under **API restrictions**, choose **Restrict key**. In the list, check **Places API (New)** only. Click **OK**.
7. Under **Application restrictions**, leave it on **None**. (The key service runs in Google Cloud, which has no fixed address.)
8. Click **Save**.
9. Keep this window open. You'll paste the key in step A5, and after that it lives only in Secret Manager. You don't need to save it anywhere else.

### A2. Get the TypeSafe (JEV) key ready
1. Sign in to **typesafe.ai** and copy your API key.
2. Keep it ready. You'll paste it in step A5.
3. No TypeSafe key yet? That's fine. Skip it now and add it later (see Part D3).

### A3. Open Cloud Shell
1. In the Google Cloud website, look at the top-right corner. Click the **>_** icon. It says **Activate Cloud Shell**.
2. A black command window opens at the bottom of the page. Wait until you see a line ending in **$**.
3. Make sure you're in the right project. Type this, but replace `YOUR-PROJECT-ID` with the project's ID (it's shown in the project picker), and press **Enter**:
   ```
   gcloud config set project YOUR-PROJECT-ID
   ```
4. If a box asks to **Authorize**, click **Authorize**.

### A4. Download the setup files
Copy this line, paste it into Cloud Shell, and press **Enter**:
```
git clone https://github.com/Clikdata2/dhap-gbp-skill.git && cd dhap-gbp-skill
```
You should see the line end with `dhap-gbp-skill $`.

### A5. Run the setup
Paste this and press **Enter**:
```
bash service/deploy.sh
```
The setup will:
1. Turn on the Google services it needs. Wait about 1 minute.
2. Ask: **"Paste the NEW Google Places key"**. Paste the key from A1 and press **Enter**. *(You won't see it as you paste. That's normal.)*
3. Ask: **"Paste the TypeSafe key"**. Paste the key from A2 and press **Enter**. Or just press **Enter** to skip.
4. Make the first team code.
5. Build and start the key service. Wait 2 to 4 minutes.

At the end you'll see a box like this:
```
================ DONE ================
Service address:  https://dhap-key-service-xxxxxxxx-uc.a.run.app
Team code:        dhap_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Health check:     {"ok": true, "places_key": true, "jev_key": true, "team_codes": 1}
```
- `"places_key": true` means the Places key is loaded.
- `"jev_key": true` means the TypeSafe key is loaded. It says `false` if you skipped it.

### A6. Nothing to write down
Both keys and the team codes are now saved in **Secret Manager**. To look at them later: in the Google Cloud website click the menu (☰) → **Security** → **Secret Manager**. The first team code is named **team** (it's for testing; you can remove it later with `bash service/team-code.sh remove team`).

### A7. Make one team code per person
Each employee gets their own code, so you can turn one person off without bothering anyone else. Each person needs a **Google account** (their work Google email is best).

In Cloud Shell, for each person, type their first name and their Google email (no spaces in the name):
```
bash service/team-code.sh add maria maria@yourcompany.com
```
What happens:
- Their code is saved in Secret Manager as **dhap-code-maria**.
- **Only maria's Google account** can read it.
- It prints a short message for you to send to maria. **That message has no secrets in it**, so email or Slack is fine.

Also make one for Ask AI, using the email of the person who manages GoHighLevel:
```
bash service/team-code.sh add askai ghl-admin@yourcompany.com
```

### A8. Set a spending alert
1. In the Google Cloud website, click the menu (☰), then **Billing**, then **Budgets & alerts**.
2. Click **Create budget**. Name it **DHAP key service**.
3. Set the amount to **$25** per month (Places costs about $0.02 a check after the first 1,000 free each month).
4. Keep the alerts at **50%, 90% and 100%**, with emails to you. Click **Finish**.

### A9. Delete the old Places key
1. Go back to **APIs & Services → Credentials**.
2. Find the **old** Places key (the one that ends in **…sNRY**). Click the trash can, then **Delete**.
3. This step matters: the old key was shared in a chat.

✅ **Part A is done.**

---

## Part B — Set up a Mac or Windows PC for Claude Code and Codex (each employee, one time)

**You need:** the message your CTO sent you, and your work Google account.

**First, get your code (2 minutes):**
1. Open **https://shell.cloud.google.com** in your web browser. Sign in with the Google account your CTO used.
2. If it asks you to accept terms or to **Authorize**, click to agree.
3. Wait for the black window to show a line ending in **$**.
4. Copy the line from your CTO's message (it starts with `gcloud secrets versions access`), paste it in, and press **Enter**.
5. You'll see two lines: **Service address:** and **Team code:**. (If you see only the first line, run the line again with `; echo` added at the end.) Keep this tab open. You'll copy from it in a moment.

**Then set up your Mac:**

1. Open the **Terminal** app (press **Command + Space**, type **Terminal**, press **Enter**).
2. Download the setup files. Paste this and press **Enter**:
   ```
   git clone https://github.com/Clikdata2/dhap-gbp-skill.git ~/dhap-gbp-skill
   ```
   *(If it says the folder already exists, that's fine. Keep going.)*
3. Run the setup. Paste this and press **Enter**:
   ```
   bash ~/dhap-gbp-skill/service/setup-employee.sh
   ```
4. When it asks, paste the **service address** and press **Enter**.
5. When it asks, paste **your team code** and press **Enter**. *(You won't see it as you paste.)*
6. Wait for **"Connection works."** and **"Done."**
7. **Quit and reopen** Terminal, Claude Code and Codex, so they read the new settings.
8. **Check it worked.** In Terminal, paste this and press **Enter**:
   ```
   echo $DHAP_SERVICE_URL
   ```
   You should see the service address. If the line is blank, run step 3 again.

✅ From now on, every DHAP run in Claude Code or Codex uses the key service on its own. Nothing else to do.

**On a Windows PC instead of a Mac** (do the "get your code" steps above first):
1. Open **PowerShell** (click Start, type **PowerShell**, press **Enter**).
2. Download the setup files. Paste this and press **Enter**:
   ```
   git clone https://github.com/Clikdata2/dhap-gbp-skill.git $HOME\dhap-gbp-skill
   ```
   *(If it says git isn't found, install it from **git-scm.com**, then try again.)*
3. Run the setup. Paste this and press **Enter**:
   ```
   powershell -ExecutionPolicy Bypass -File $HOME\dhap-gbp-skill\service\setup-employee.ps1
   ```
4. Paste the **service address**, press **Enter**. Paste **your team code**, press **Enter**.
5. Wait for **"Connection works."** and **"Done."**
6. **Quit and reopen** PowerShell, Claude Code and Codex.
7. **Check it worked:** in a new PowerShell window, run `echo $env:DHAP_SERVICE_URL`. You should see the service address.

**If something goes wrong**
| You see | What it means | What to do |
|---|---|---|
| "the team code is wrong" | The code was mistyped or turned off | Run the line from your CTO's message again in Cloud Shell and copy the code carefully. Still failing? Ask the CTO for a new code. |
| "Could not reach the service" | Wrong address or no internet | Check the address starts with `https://` and you're online. |
| The report says Places or JEV was **skipped** | The check couldn't run this time | The report is still fine. Those checks never change a score. Tell the CTO if it keeps happening. |

---

## Part C — Set up Ask AI (GHL admin, one time)

**You need:** the message the CTO sent you for **askai**. First get the values: open **https://shell.cloud.google.com**, sign in with the email the CTO used, paste the line from the message, and press **Enter**. You'll see the **Service address** and the **Team code**.

### C1. Save the two values in GHL
1. In GoHighLevel, open the sub-account you run DHAP reports in.
2. Go to **Settings → Custom Values**.
3. Click **Add Custom Value**. Name: **DHAP Service URL**. Value: the service address. Save.
4. Click **Add Custom Value** again. Name: **DHAP Team Code**. Value: the **askai** team code. Save.

### C2. Test it once in Ask AI
1. Open **Ask AI**.
2. Type this, but replace the two parts in CAPITALS with the real values:
   ```
   Send a GET request to SERVICE-ADDRESS/lookup?q=James%20Mitsubishi%20Greece%20NY
   with the header X-DHAP-Code: ASKAI-TEAM-CODE
   and show me exactly what it returns.
   ```
3. You should see `"status": "ok"` with the dealer's name, phone and rating. ✅ Done. Ask AI will use the key service on every DHAP run.
4. If you see `"missing or wrong team code"`, copy the code again (see "You need" above) and update the **DHAP Team Code** Custom Value.

> We tested this on October 21, 2026: Ask AI sends real web requests and can put the team code in a header, so the code stays out of the service's logs.

---

## Part D — Everyday jobs (CTO)
All of these are typed in **Cloud Shell**, inside the `dhap-gbp-skill` folder. If you just opened Cloud Shell, first type `cd dhap-gbp-skill` and press **Enter**.

**D1. Someone leaves, or a code leaked**
```
bash service/team-code.sh remove maria
```
Their code stops working within about a minute, and their saved copy in Secret Manager is deleted. If they still need access, make a new one with `add`.

**D2. See who has a code**
```
bash service/team-code.sh list
```
It shows names only, never the codes.

**D3. Change or add a key (Places or TypeSafe)**
```
git pull
bash service/deploy.sh
```
Paste only the key you're changing. For the other one, just press **Enter** to keep it. Team codes don't change.

**D4. Check that the service is working**
Open the service address with `/health` added at the end in any web browser, for example `https://dhap-key-service-xxxx.a.run.app/health`. You want `"ok": true`. This page never shows keys or codes.

---

## For the technical reader
- Code: `service/main.py`, a Google Cloud Run function (Python 3.12). Keys and codes live in Secret Manager as `dhap-places-key`, `dhap-typesafe-key` and `dhap-team-codes` (JSON `{name: code}`).
- Routes: `GET /health` · `POST /places/v1/places:searchText` and `GET /places/v1/places/<id>` (forwarded to Places API (New), nothing else is allowed) · `POST /jev` (forwarded to TypeSafe System One, pinned model only) · `GET /lookup?q=` (one compact answer for Ask AI). Every route except `/health` needs a team code (`X-DHAP-Code` header; `?code=` is accepted on `/lookup` only). Logs record the team member's name and route, never keys or codes.
- Engine: `engine/places.py` and `engine/jev.py` use the service when `DHAP_SERVICE_URL` and `DHAP_TEAM_CODE` are set. Otherwise they fall back to `GOOGLE_PLACES_API_KEY` / `TYPESAFE_API_KEY` on the machine. If neither is set, they skip, and the audit goes on.
- Team codes: the master list is the secret `dhap-team-codes` (read by the service). Each person's copy is the secret `dhap-code-NAME` with only that person's Google account as Secret Accessor. No password manager is needed.
- The service is open to the internet but useless without a team code. Max 3 instances; Places spending is capped by the budget alert and by Google's quotas.
- If `deploy.sh` stops with an error about **allUsers** or **allow-unauthenticated**, your organization blocks public services. An admin must allow it for this one service: Organization policy "Domain restricted sharing".
