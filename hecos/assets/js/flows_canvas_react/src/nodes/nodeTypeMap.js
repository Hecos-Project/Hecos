/**
 * Maps action prefix → ReactFlow node type name
 */
export const ACTION_TYPE_MAP = {
  TRIGGER:    'triggerNode',
  CONTROL:    'triggerNode',
  LOGIC:      'logicNode',
  FLOWS:      'actionNode',
  AI:         'aiNode',
  AUDIO:      'actionNode',
  MAIL:       'actionNode',
  MESSENGER:  'actionNode',
  CALENDAR:   'actionNode',
  REMINDER:   'actionNode',
  WEATHER:    'actionNode',
  EXECUTOR:   'actionNode',
  BROWSER:    'actionNode',
  WEBCAM:     'actionNode',
  MEMORY:     'actionNode',
  SYSTEM:     'actionNode',
  AUTOMATION: 'actionNode',
  MEDIA:      'actionNode',
  DATA:       'actionNode',
  PLUGINS:    'actionNode',
  GENERAL:    'actionNode',
  USER:       'actionNode',
};

// Category color map for badge colors on node header
export const CATEGORY_COLORS = {
  TRIGGER:    { bg: '#4c1d95', text: '#c4b5fd' },
  CONTROL:    { bg: '#3730a3', text: '#a5b4fc' },
  LOGIC:      { bg: '#78350f', text: '#fcd34d' },
  FLOWS:      { bg: '#064e3b', text: '#6ee7b7' },
  AI:         { bg: '#581c87', text: '#e879f9' },
  AUDIO:      { bg: '#134e4a', text: '#5eead4' },
  MAIL:       { bg: '#14213d', text: '#93c5fd' },
  MESSENGER:  { bg: '#14213d', text: '#6ee7b7' },
  TIME:       { bg: '#1e1b4b', text: '#a5b4fc' },
  SYSTEM:     { bg: '#1c1c1c', text: '#d4d4d8' },
  DATA:       { bg: '#0c4a6e', text: '#7dd3fc' },
  BROWSER:    { bg: '#172554', text: '#93c5fd' },
  VISION:     { bg: '#1a1a00', text: '#fde68a' },
  MEMORY:     { bg: '#1c0538', text: '#d8b4fe' },
  AUTOMATION: { bg: '#0a0a0a', text: '#e2e8f0' },
  MEDIA:      { bg: '#0c1a2e', text: '#7dd3fc' },
  PLUGINS:    { bg: '#1a0a00', text: '#fdba74' },
  HTTP:       { bg: '#134e4a', text: '#6ee7b7' },
  USER:       { bg: '#4c1d95', text: '#e879f9' },
};

export function getCategoryFromAction(actionName) {
  return actionName?.split('__')[0] || 'GENERAL';
}

export function getNodeTypeFromAction(actionName) {
  if (!actionName) return 'actionNode';
  const prefix = actionName.split('__')[0];

  // Special cases within LOGIC
  if (prefix === 'LOGIC') {
    const method = actionName.split('__')[1] || '';
    if (method === 'http_request') return 'httpNode';
    if (method === 'delay')        return 'delayNode';
    if (method === 'set_variable' || method === 'template') return 'varNode';
    return 'logicNode';
  }

  return ACTION_TYPE_MAP[prefix] || 'actionNode';
}
