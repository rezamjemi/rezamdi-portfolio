# RezaMDI portfolio

Your photography website with its own admin page.

- **The site**: home page with the best of each category, plus a page per category.
- **The admin** at `yoursite/admin`: log in with GitHub to add photos, change titles, pick your
  "Best of" shots, add filter versions and edit your intro, about text and Instagram link.
  The site rebuilds itself about a minute after you press **Publish**.

## One-time setup (about 20 minutes)

### 1. Put the project on GitHub
1. Create a free account at github.com if you don't have one.
2. Top right **+** → **New repository**. Name it exactly `rezamdi-portfolio`. Private or public both work. Click **Create repository**.
3. On the empty repository page click **uploading an existing file**.
4. Unzip this project on your computer, open the folder, select **everything inside it**
   (admin, content, photos, src, build.py, netlify.toml, requirements.txt, README.md, .gitignore)
   and drag it onto the page. Wait for the uploads to finish, then click **Commit changes**.

### 2. (Already done)
The admin is already set to your GitHub account `rezamjemi` and the repository name `rezamdi-portfolio`.
If you name the repository something else, change the `repo:` line in `admin/config.yml` to match.

### 3. Connect Netlify
1. Log in at app.netlify.com (sign in with GitHub is easiest).
2. **Add new project** → **Import an existing project** → **GitHub** → choose `rezamdi-portfolio`.
3. Leave the build settings as they are (they come from `netlify.toml`) and click **Deploy**.
4. After 1–2 minutes your site is live. In **Project configuration → General** you can rename it,
   e.g. `rezamdi.netlify.app`. Note the address.

### 4. Let the admin log in with GitHub
1. Open github.com/settings/developers → **OAuth Apps** → **New OAuth App**.
   - Application name: `RezaMDI admin`
   - Homepage URL: your Netlify address, e.g. `https://rezamdi.netlify.app`
   - Authorization callback URL: `https://api.netlify.com/auth/done`
2. Click **Register application**, then **Generate a new client secret**. Keep this page open.
3. In Netlify: **Project configuration → Security → OAuth** (may be listed as *Access & security*)
   → **Install provider** → **GitHub** → paste the **Client ID** and **Client secret** → **Install**.

### 5. Use it
Go to `https://your-address/admin`, click **Login with GitHub**, and you're in.

## Everyday use
- **Add a photo**: Photos → **New Photo** → upload, title, category → **Publish**.
- **Best of a category**: open the photo, turn on **Best of category**. Turn it off on the old one.
- **Home page picks**: turn on **Home page pick** for up to three photos per category.
- **Order**: lower numbers show first (10, 20, 30…).
- **Filter versions**: in a photo, add versions under **Filter versions**, and name the main one
  in **Name of this version**.
- **Remove a photo**: turn on **Hide from site** (keeps it in the admin), or delete it.
- **Text**: Site text → Name, intro and about.

## Good to know
- Netlify's free plan allows roughly 20 updates a month. Every **Publish** is one update, so add
  a batch of photos in one sitting when you can.
- Camera details are read from the photo automatically. Phone screenshots and photos exported
  from Instagram usually have none, so that line is simply left out.
- Your own domain: Netlify → **Domain management → Add a domain** and follow the steps.
- To check a build on your computer: `pip install Pillow` then `python3 build.py`; the site appears in `dist/`.
