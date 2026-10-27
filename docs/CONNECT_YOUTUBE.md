# Connect your YouTube channel (optional)

Signal Studio can read **your own videos** (title, publish date, views, likes, comments) so the forecast is adjusted to
**your** channel. There are two ways to give it your data:

| Way | Needs setup? | What the app sees |
| --- | --- | --- |
| **Upload** a YouTube Studio export (CSV or the zipped export folder) | No | Only the file you upload |
| **Connect with Google** | Yes, once (below) | Your video list. By default it is read once and the access is cancelled; on your own computer you can choose **Keep me connected** (see below) |

Uploading works everywhere with no setup. The steps below are only for the direct connection.

## What the connection does (and does not do)

- It asks for one permission: **read-only access to your YouTube account's videos** (`youtube.readonly`). It cannot change, delete or upload anything.
- By default it reads your latest videos once (about 9 of the 10,000 free API units a day for 200 videos), copies them into your browser session, and **immediately cancels its own access**. No password and no long-lived token is stored anywhere. (The optional **Keep me connected** mode below changes that on purpose, and only on your own computer.)
- Your videos are kept in memory for your session only. They are not written to disk or to logs. Press **Remove my data** to forget them.
- **There is no time limit on signing in.** Take as long as you like on Google's screen; the app does not give up after a few minutes. (The app's own access ends right after it reads your videos; that is a privacy choice, not a timer. Pressing **Connect with Google** again reads your latest videos again whenever you want.)
- On the hosted website your data passes through that server's memory. If you prefer it never to leave your computer, run the app locally (`run.ps1` / `run.sh`).

## Keep me connected (your own computer only)

Pressing **Connect with Google** every time is not necessary. On your own computer the app can stay connected between visits:

1. In `.env` add `GOOGLE_STAY_CONNECTED=1` (see `.env.example`).
2. Open **My channel** and tick **Keep me connected on this computer** (it is ticked by default), then **Connect with Google** and allow it once.
3. From then on, every time you open the app your channel loads by itself, with no sign-in screen. Your videos are read fresh each time.

What is saved: only Google's read-only permission slip (a "refresh token") in a private file in **your own user folder**,
`~/.signal_studio/google_connection.json` (on Windows: the `.signal_studio` folder inside your user folder, `C:/Users/<you>/`). It is outside the project and outside git.
**Your videos, titles and view counts are never saved**, and the short-lived access token is never written anywhere.

Safety rules built in:

- It works **only for a visitor on the same computer**. If someone opens the app from another device on your network, or on the hosted website, the saved connection is never used and the option is not shown. The hosted website never switches the setting on.
- **Disconnect from Google** (in the My channel tab) cancels the permission at Google, deletes the file and forgets the loaded channel. You can also remove it yourself any time under *Google Account > Security > Your connections to third-party apps* (the page lists it as "Signal Studio").
- **Remove my data** only forgets the channel in the current browser tab; the saved connection stays until you press Disconnect.
- If Google ends the permission (for example you removed it in your account), the app deletes the dead file and asks you to connect again. A short internet problem keeps the file.
- **Testing mode limit set by Google, not by this app:** while the Google Cloud app is in *Testing* mode, Google expires a saved permission after **7 days**, and you sign in again. Setting the app's publishing status to *In production* removes that 7-day limit (the app stays "unverified", which is fine for personal use, and the 100-user cap still applies). To remove it all, delete the `.signal_studio` file or press Disconnect.

## One-time setup (about 10 minutes, free)

You do this in your own Google account. **Never paste the client secret into a chat or commit it to git.**

1. Open <https://console.cloud.google.com/> and create a project (for example "Signal Studio").
2. **APIs & Services -> Library**: search for **YouTube Data API v3** and click **Enable**.
3. **APIs & Services -> OAuth consent screen**: choose **External**, fill in the app name and your email, and keep the publishing status on **Testing**.
   Under **Test users** add the Google account(s) that own the channel(s) you want to connect (up to 100).
4. **APIs & Services -> Credentials -> Create credentials -> OAuth client ID**: type **Web application**.
   Under **Authorised redirect URIs** add the exact address of the app:
   - local run: `http://localhost:8501/` (use the port you start the app on)
   - hosted website: `https://youtube-strategy-predictor.onrender.com/`
5. Copy the **Client ID** and **Client secret**.
6. Copy `.env.example` to `.env` (this file is git-ignored) and fill in:

   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8501/
   ```

   For the hosted website, set the same three values as environment variables in the Render dashboard instead (never in git).
7. Start the app (`run.ps1` / `run.sh`), open the **My channel** tab, press **Connect with Google**, then **Continue to Google**.

## What you will see

- While the app is in **Testing** mode Google shows a notice that the app is **not verified**. This is normal for a personal or class project;
  click **Advanced** and continue with the test account. Making the app public would require Google's verification, which is not needed here.
- Only the test users you listed can sign in.
- If something is wrong the app shows a plain message (for example "the redirect address does not match": the address in step 4 must be identical to `GOOGLE_REDIRECT_URI`).

## Rules the app follows (YouTube API Services Developer Policies)

- Data from the API is not stored beyond the session (the policies allow keeping most API data for at most 30 days).
- No dataset is built from API data, and the models are **not** trained on it: they were trained on a public dataset. Your videos are only
  used, in your session, to describe your channel's usual level.
- By default access is cancelled right after reading. With **Keep me connected** the only thing stored is the permission slip, on your own computer, and Disconnect cancels it. **Remove my data** deletes the loaded copy.
