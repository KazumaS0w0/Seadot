# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

## Seadot download controls

- Double-click a download row to open its details window. Use the title-bar controls to minimize, restore, or close it.
- Add Link asks for a filename, destination folder, and split count before starting. Split downloads use HTTP Range when the server supports it and fall back to a regular stream otherwise.
- If the destination filename already exists, choose to overwrite it, save a numbered copy, or cancel.
- The details window lets you set a per-download speed limit and choose an optional power action after downloads finish. Power actions are opt-in and can be cancelled from Options.
- Settings → Browser extension opens Chrome or Edge extension settings and shows the local extension folder. Enable Developer mode, choose Load unpacked, and select `seadot-extension`; this is a local development extension and is not distributed through either Web Store.
- Removing selected downloads asks whether to remove only their Seadot records or also delete the files from disk.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
