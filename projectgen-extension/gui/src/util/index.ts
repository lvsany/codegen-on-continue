export function getMetaKeyLabel() {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  return isMac ? '⌘' : 'Ctrl';
}

export function isMetaEquivalentKeyPressed(event: KeyboardEvent | React.KeyboardEvent) {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  return isMac ? event.metaKey : event.ctrlKey;
}
