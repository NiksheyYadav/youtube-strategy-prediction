# Signal Studio: privacy policy

*Last updated: 27 October 2026.*

Signal Studio is a student project that forecasts how a YouTube video may perform before it is published. It is made by Nikshey Yadav.
Contact: relativity1905e@gmail.com

This page says exactly what the app does with your information. It is short because the app collects very little.

## What the app can read

If you choose **Connect with Google**, the app asks for one permission: **read-only access to your YouTube account**
(`https://www.googleapis.com/auth/youtube.readonly`). From that it reads only:

- the title of your channel, and
- for your latest videos: the title, publish date, duration, and the numbers of views, likes and comments.

It cannot change, upload or delete anything, and it does not read your email, files, contacts, or anything outside YouTube.

If you upload a YouTube Studio export instead, the app reads only that file.

## What it does with it

- It uses those numbers **only to show you a forecast for your own channel** in the page you are looking at (your usual level of views, and how much a draft title may add or lose).
- It does **not** use your data to train or improve any model. The models were trained once, on a public dataset of trending videos from 2017-2018.
- It does **not** sell, share, publish or give your data to anyone, and it does not use it for advertising.
- No person reads your data.

## What is stored, and for how long

- **Your videos and numbers are not stored.** They are held in memory for as long as your browser tab is open, then forgotten. They are not written to disk, to logs or to a database. The button **Remove my data** forgets them at once.
- **By default the app cancels its own Google access straight after reading your videos.**
- **Optional "Keep me connected" (only when you run the app on your own computer):** if you tick it, the app saves Google's read-only permission slip (a "refresh token") in a private file in your own user folder (`~/.signal_studio/google_connection.json`) so you do not have to sign in again. Your videos are never saved there. The hosted website never offers this and never stores a token.
- The hosted website processes your data in its server's memory while you use it. If you prefer that it never leaves your computer, run the app locally (see the README).

## Your control

- **Disconnect from Google** in the app's *My channel* tab cancels the permission at Google, deletes the saved file and forgets your data.
- You can also remove the permission yourself at any time: Google Account, then Security, then *Your connections to third-party apps and services*, then Signal Studio, then *Delete all connections*.
- To delete everything the app keeps on your computer, press Disconnect or delete the folder `.signal_studio` in your user folder.

## Google API Services User Data Policy

Signal Studio's use and transfer of information received from Google APIs adheres to the
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy), including its Limited Use
requirements. The app also follows the [YouTube API Services Terms of Service](https://developers.google.com/youtube/terms/api-services-terms-of-service)
and [Google Privacy Policy](https://policies.google.com/privacy): data from the YouTube API is not kept beyond your session and no dataset is built from it.

## Children

The app is not directed at children.

## Changes

If this policy changes, the new version will be published in this file with a new date. The full history is visible in the project's repository.

## Source code

The code that does everything described here is public: https://github.com/NiksheyYadav/youtube-strategy-prediction
