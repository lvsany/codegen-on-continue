/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // VS Code theme colors
        background: "var(--vscode-sideBar-background, #1e1e1e)",
        foreground: "var(--vscode-sideBar-foreground, #e6e6e6)",
        "editor-background": "var(--vscode-editor-background, #1e1e1e)",
        primary: "var(--vscode-button-background, #2c5aa0)",
        "primary-foreground": "var(--vscode-button-foreground, #ffffff)",
        "primary-hover": "var(--vscode-button-hoverBackground, #3a6db3)",
        border: "var(--vscode-sideBar-border, #2a2a2a)",
        "border-focus": "var(--vscode-focusBorder, #3a6db3)",
        input: "var(--vscode-input-background, #2d2d2d)",
        "input-foreground": "var(--vscode-input-foreground, #e6e6e6)",
        "input-border": "var(--vscode-input-border, #555555)",
        description: "var(--vscode-descriptionForeground, #b3b3b3)",
        "description-muted": "var(--vscode-list-deemphasizedForeground, #8c8c8c)",
        "list-hover": "var(--vscode-list-hoverBackground, #383838)",
        "list-active": "var(--vscode-list-activeSelectionBackground, rgba(44, 90, 160, 0.3))",
        "list-active-foreground": "var(--vscode-list-activeSelectionForeground, #ffffff)",
        "badge-background": "var(--vscode-badge-background, #4d4d4d)",
        "badge-foreground": "var(--vscode-badge-foreground, #ffffff)",
        success: "var(--vscode-testing-iconPassed, #4caf50)",
        warning: "var(--vscode-editorWarning-foreground, #ffb74d)",
        error: "var(--vscode-editorError-foreground, #f44336)",
      },
      borderRadius: {
        default: "0.5rem",
      },
      fontSize: {
        "2xs": "0.625rem",
      },
    },
  },
  plugins: [],
};
