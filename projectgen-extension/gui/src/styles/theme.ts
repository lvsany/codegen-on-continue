// VS Code theme colors with fallback defaults
export const THEME_COLORS = {
  background: {
    vars: ["--vscode-sideBar-background", "--vscode-editor-background"],
    default: "#1e1e1e",
  },
  foreground: {
    vars: ["--vscode-sideBar-foreground", "--vscode-editor-foreground"],
    default: "#e6e6e6",
  },
  "editor-background": {
    vars: ["--vscode-editor-background"],
    default: "#1e1e1e",
  },
  "primary-background": {
    vars: ["--vscode-button-background"],
    default: "#2c5aa0",
  },
  "primary-foreground": {
    vars: ["--vscode-button-foreground"],
    default: "#ffffff",
  },
  border: {
    vars: ["--vscode-sideBar-border", "--vscode-panel-border"],
    default: "#2a2a2a",
  },
  "border-focus": {
    vars: ["--vscode-focusBorder"],
    default: "#3a6db3",
  },
  "command-border": {
    vars: ["--vscode-commandCenter-inactiveBorder"],
    default: "#555555",
  },
  description: {
    vars: ["--vscode-descriptionForeground"],
    default: "#b3b3b3",
  },
  "description-muted": {
    vars: ["--vscode-list-deemphasizedForeground"],
    default: "#8c8c8c",
  },
  "input-background": {
    vars: ["--vscode-input-background"],
    default: "#2d2d2d",
  },
  "input-foreground": {
    vars: ["--vscode-input-foreground"],
    default: "#e6e6e6",
  },
  "list-active": {
    vars: ["--vscode-list-activeSelectionBackground"],
    default: "#2c5aa050",
  },
  "list-active-foreground": {
    vars: ["--vscode-list-activeSelectionForeground"],
    default: "#ffffff",
  },
};

export const defaultBorderRadius = "0.5rem";
export const lightGray = "#999998";

// Generate CSS variable with fallback
export const getRecursiveVar = (vars: string[], defaultColor: string) => {
  return [...vars].reverse().reduce((curr, varName) => {
    return `var(${varName}, ${curr})`;
  }, defaultColor);
};

export const varWithFallback = (colorName: keyof typeof THEME_COLORS) => {
  const themeVals = THEME_COLORS[colorName];
  if (!themeVals) {
    throw new Error(`Invalid theme color name ${colorName}`);
  }
  return getRecursiveVar(themeVals.vars, themeVals.default);
};

// Export styled-components compatible variables
export const vscInputBackground = varWithFallback("input-background");
export const vscBackground = varWithFallback("background");
export const vscForeground = varWithFallback("foreground");
export const vscButtonBackground = varWithFallback("primary-background");
export const vscButtonForeground = varWithFallback("primary-foreground");
export const vscEditorBackground = varWithFallback("editor-background");
export const vscListActiveBackground = varWithFallback("list-active");
export const vscListActiveForeground = varWithFallback("list-active-foreground");
export const vscCommandCenterInactiveBorder = varWithFallback("command-border");
