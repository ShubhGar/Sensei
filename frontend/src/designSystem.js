/**
 * Design System Constants
 * Centralized design tokens for consistent UI across the application
 */

export const DESIGN_TOKENS = {
  // Spacing scale (8px base unit)
  spacing: {
    xs: 0.5,   // 4px
    sm: 1,     // 8px
    md: 1.5,   // 12px
    lg: 2,     // 16px
    xl: 3,     // 24px
    xxl: 4,    // 32px
  },
  
  // Border radius
  borderRadius: {
    sm: 8,     // Small elements (buttons, chips)
    md: 12,    // Cards, containers (matches theme)
    lg: 16,    // Large containers
  },
  
  // Shadows (consistent elevation)
  shadows: {
    sm: '0 1px 3px rgba(0,0,0,0.1)',
    md: '0 2px 8px rgba(0,0,0,0.06)',
    lg: '0 4px 16px rgba(0,0,0,0.1)',
    xl: '0 6px 24px rgba(0,0,0,0.15)',
  },
  
  // Dark mode shadows
  shadowsDark: {
    sm: '0 1px 3px rgba(0,0,0,0.3)',
    md: '0 2px 8px rgba(0,0,0,0.3)',
    lg: '0 4px 16px rgba(0,0,0,0.3)',
    xl: '0 6px 24px rgba(0,0,0,0.4)',
  },
  
  // Transitions
  transitions: {
    fast: '0.15s ease',
    normal: '0.2s ease',
    slow: '0.3s cubic-bezier(0.4, 0, 0.2, 1)',
  },
};

/**
 * Get standardized card background based on theme mode
 */
export const getCardBackground = (mode) => {
  return mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #2A2A2A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #F5F7F8 100%)';
};

/**
 * Get highlight card background (for emphasized cards)
 */
export const getHighlightCardBackground = (mode) => {
  return mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #1E3A3A 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #E8F5E9 100%)';
};

/**
 * Get risk/warning card background
 */
export const getRiskCardBackground = (mode) => {
  return mode === 'dark'
    ? 'linear-gradient(135deg, #1E1E1E 0%, #3A2A1E 100%)'
    : 'linear-gradient(135deg, #FFFFFF 0%, #FFF3E0 100%)';
};

/**
 * Standard card styles
 */
export const getCardStyles = (mode, variant = 'default') => {
  const backgrounds = {
    default: getCardBackground(mode),
    highlight: getHighlightCardBackground(mode),
    risk: getRiskCardBackground(mode),
  };
  
  return {
    background: backgrounds[variant] || backgrounds.default,
    borderRadius: DESIGN_TOKENS.borderRadius.md,
    boxShadow: mode === 'dark' 
      ? DESIGN_TOKENS.shadowsDark.md 
      : DESIGN_TOKENS.shadows.md,
    transition: DESIGN_TOKENS.transitions.slow,
    '&:hover': {
      boxShadow: mode === 'dark'
        ? DESIGN_TOKENS.shadowsDark.lg
        : DESIGN_TOKENS.shadows.lg,
      transform: 'translateY(-2px)',
    },
  };
};

/**
 * Standard button spacing
 */
export const BUTTON_SPACING = {
  padding: '10px 24px',
  gap: 1, // 8px
};

/**
 * Standard typography variants
 */
export const TYPOGRAPHY = {
  h4: { fontWeight: 700, letterSpacing: '-0.02em' },
  h5: { fontWeight: 600, letterSpacing: '-0.01em' },
  h6: { fontWeight: 600, letterSpacing: '-0.01em' },
  subtitle1: { fontWeight: 600 },
  subtitle2: { fontWeight: 500 },
  body1: { fontWeight: 400 },
  body2: { fontWeight: 400 },
  button: { fontWeight: 600, textTransform: 'none' },
};

