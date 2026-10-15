# Zombie Apocalypse (web version)

This is the pygame game converted with pygbag so it runs in a browser.

## Deploy on Vercel
1. Put this folder in a GitHub repo (main.py and vercel.json at the top level).
2. On vercel.com, click Add New > Project and import the repo.
3. Leave Framework Preset as "Other" and click Deploy.
   vercel.json already tells Vercel to install pygbag, build the game,
   and serve the build/web folder.

## Test it on your computer first (optional)
    pip install pygbag
    pygbag .
Then open http://localhost:8000 in your browser.

## If the Vercel build fails
Build it yourself and upload only the finished site:
    pip install pygbag
    pygbag --build .
    cd build/web
    npx vercel --prod

Note: the first load takes a few seconds, and you have to click the page once
before the game starts (browsers need a click before a game can take input).
