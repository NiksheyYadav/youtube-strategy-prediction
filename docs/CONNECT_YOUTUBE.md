# Connect your YouTube channel (optional)

Signal Studio can read **your own videos** (title, publish date, views, likes, comments) so the forecast is adjusted to
**your** channel. There are two ways to give it your data:

| Way | Needs setup? | What the app sees |
| --- | --- | --- |
| **Upload** a YouTube Studio export (CSV or the zipped export folder) | No | Only the file you upload |
| **Connect with Google** | Yes, once (below) | Your video list, read once, then the access is cancelled |

Uploading works everywhere with no setup. The steps below are only for the direct connection.

## What the connection does (and does not do)

- It asks for one permission: **read-only access to your YouTube account's videos** (`youtube.readonly`). It cannot change, delete or upload anything.
- It reads your latest videos once (about 9 of the 10,000 free API units a day for 200 videos), copies them into your browser session, and **immediately cancels its own access**. No password and no long-lived token is stored anywhere.
- Your videos are kept in memory for your session only. They are not written to disk or to logs. Press **Remove my data** to forget them.
- On the hosted demo your data passes through that server's memory. If you prefer it never to leave your computer, run the app locally (`run.ps1` / `run.sh`).

## One-time setup (about 10 minutes, free)

You do this in your own Google account. **Never paste the client secret into a chat or commit it to git.**

1. Open <https://console.cloud.google.com/> and create a project (for example "Signal Studio").
2. **APIs & Services -> Library**: search for **YouTube Data API v3** and click **Enable**.
3. **APIs & Services -> OAuth consent screen**: choose **External**, fill in the app name and your email, and keep the publishing status on **Testing**.
   Under **Test users** add the Google account(s) that own the channel(s) you want to connect (up to 100).
4. **APIs & Services -> Credentials -> Create credentials -> OAuth client ID**: type **Web application**.
   Under **Authorised redirect URIs** add the exact address of the app:
   - local run: `http://localhost:8501/` (use the port you start the app on)
   - hosted demo: `https://youtube-strategy-predictor.onrender.com/`
5. Copy the **Client ID** and **Client secret**.
6. Copy `.env.example` to `.env` (this file is git-ignored) and fill in:

   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8501/
   ```

   For the hosted demo, set the same three values as environment variables in the Render dashboard instead (never in git).
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
- Access is cancelled right after reading, and **Remove my data** deletes the copy.
