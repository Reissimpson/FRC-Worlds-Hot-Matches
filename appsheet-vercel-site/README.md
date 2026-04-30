# FRC Hot Matches AppSheet Vercel Wrapper

This is a small static site that embeds your AppSheet app in a public Vercel page.

## 1. Add Your AppSheet URL

Open `config.js` and replace:

```js
appsheetUrl: "https://www.appsheet.com/start/YOUR_APP_ID"
```

with your AppSheet browser link.

## 2. Enable AppSheet Embedding

In AppSheet:

1. Open the app editor.
2. Go to **Security > Options**.
3. Enable **Allow app embedding**.
4. Save the app.

For public viewing, also make sure your AppSheet sharing/security settings allow the audience you want.

## 3. Deploy To Vercel

From this folder:

```powershell
npm install
npx vercel
```

For production:

```powershell
npx vercel --prod
```

## Notes

- AppSheet public access may require an AppSheet plan that supports public apps.
- Restricted AppSheet apps may not embed correctly outside Google Sites.
- If embedding is blocked, the **Open App** button still lets visitors open the AppSheet browser link directly.
