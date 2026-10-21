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
- **Password manager** — the app your team uses to store passwords (for example 1Password).

> **Safety rules**
> 1. Never paste a key or a team code into email, Slack, a chat with an AI, or a document.
> 2. Share them only through your password manager.
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
9. Put the new key in your password manager as **"DHAP – Google Places key"**.

### A2. Get the TypeSafe (JEV) key ready
1. Sign in to **typesafe.ai** and copy your API key.
2. Put it in your password manager as **"DHAP – TypeSafe key"**.
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

### A6. Save what you got
In your password manager, create **"DHAP – Key service"** and save:
- **Service address** (the `https://` line)
- **Team code** (the `dhap_` line). This first code is named **team**.

### A7. Make one team code per person
Each employee should get their own code, so you can turn one person off without bothering anyone else. In Cloud Shell, for each person, type (use their first name, no spaces):
```
bash service/team-code.sh add maria
```
It prints **"New code for maria: dhap_..."**. Save it in the password manager and share it with that person only.

Also make one for Ask AI:
```
bash service/team-code.sh add askai
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

## Part B — Set up a Mac for Claude Code and Codex (each employee, one time)

**You need:** the service address and **your own** team code from the password manager.

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

**If something goes wrong**
| You see | What it means | What to do |
|---|---|---|
| "the team code is wrong" | The code was mistyped or turned off | Copy it again from the password manager. Still failing? Ask the CTO for a new code. |
| "Could not reach the service" | Wrong address or no internet | Check the address starts with `https://` and you're online. |
| The report says Places or JEV was **skipped** | The check couldn't run this time | The report is still fine. Those checks never change a score. Tell the CTO if it keeps happening. |

---

## Part C — Set up Ask AI (GHL admin, one time)

**You need:** the service address and the **askai** team code from A7.

### C1. Save the two values in GHL
1. In GoHighLevel, open the sub-account you run DHAP reports in.
2. Go to **Settings → Custom Values**.
3. Click **Add Custom Value**. Name: **DHAP Service URL**. Value: the service address. Save.
4. Click **Add Custom Value** again. Name: **DHAP Team Code**. Value: the **askai** team code. Save.

### C2. Test whether Ask AI can use it
1. Open **Ask AI**.
2. Type this, but replace the two parts in CAPITALS with the real values:
   ```
   Open this web address and show me exactly what it returns:
   SERVICE-ADDRESS/lookup?q=James%20Mitsubishi%20Greece%20NY&code=ASKAI-TEAM-CODE
   ```
3. **If it shows** `"status": "ok"` with the dealer's name, phone and rating: ✅ Done. Ask AI will use the key service on every DHAP run.
4. **If it says it can't open web addresses:** Ask AI can't reach outside websites by itself. Tell Travis. The next step is a small GHL workflow that makes the call for Ask AI. Until then, Ask AI runs simply skip the Places check, and the report is still correct.

> Note: in this test the team code is part of the address, so it appears in the service's log. That's why Ask AI gets **its own** code (**askai**), which you can replace at any time.

---

## Part D — Everyday jobs (CTO)
All of these are typed in **Cloud Shell**, inside the `dhap-gbp-skill` folder. If you just opened Cloud Shell, first type `cd dhap-gbp-skill` and press **Enter**.

**D1. Someone leaves, or a code leaked**
```
bash service/team-code.sh remove maria
```
Their code stops working within about a minute. Make a new one with `add` if they still need it.

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
- The service is open to the internet but useless without a team code. Max 3 instances; Places spending is capped by the budget alert and by Google's quotas.
- If `deploy.sh` stops with an error about **allUsers** or **allow-unauthenticated**, your organization blocks public services. An admin must allow it for this one service: Organization policy "Domain restricted sharing".
