import { createTheme } from '@mui/material/styles';

// PayU Sensei Color Palette - Matching PayU Branding
const lightColors = {
  primary: {
    main: '#009688',      // Teal (Primary)
    dark: '#00796B',      // Darker Teal (Hover)
    light: '#26A69A',     // Light Teal (Accent)
  },
  secondary: {
    main: '#009688',      // Teal (Secondary Accent)
    light: '#E0F2F1',     // Light Teal (Background)
  },
  background: {
    default: '#F5F7F8',   // Soft Neutral Background
    paper: '#FFFFFF',     // White (Clean UI)
    alt: '#FAFAFA',       // Alternative Background
  },
  text: {
    primary: '#333333',   // Dark Gray (Headings)
    secondary: '#666666', // Medium Gray (Secondary Text)
  },
  accent: {
    urgent: '#FF5252',    // Red (Urgent Alerts)
    info: '#2196F3',      // Blue (Info)
  },
};

const darkColors = {
  primary: {
    main: '#26A69A',      // Light Teal (Primary)
    dark: '#009688',      // Teal (Hover)
    light: '#4DB6AC',     // Lighter Teal (Accent)
  },
  secondary: {
    main: '#26A69A',      // Light Teal (Secondary Accent)
    light: '#1E3A3A',     // Dark Teal (Background)
  },
  background: {
    default: '#121212',   // Dark Background
    paper: '#1E1E1E',     // Dark Paper
    alt: '#2A2A2A',       // Alternative Dark Background
  },
  text: {
    primary: '#FFFFFF',   // White (Headings)
    secondary: '#B0B0B0', // Light Gray (Secondary Text)
  },
  accent: {
    urgent: '#FF5252',    // Red (Urgent Alerts)
    info: '#64B5F6',      // Light Blue (Info)
  },
};

const getTheme = (mode) => {
  const colors = mode === 'dark' ? darkColors : lightColors;
  
  return createTheme({
    palette: {
      mode,
      primary: {
        main: colors.primary.main,
        dark: colors.primary.dark,
        light: colors.primary.light,
        contrastText: '#FFFFFF',
      },
      secondary: {
        main: colors.secondary.main,
        light: colors.secondary.light,
        contrastText: '#FFFFFF',
      },
      background: {
        default: colors.background.default,
        paper: colors.background.paper,
      },
      text: {
        primary: colors.text.primary,
        secondary: colors.text.secondary,
      },
      error: {
        main: colors.accent.urgent,
      },
      warning: {
        main: '#FF9800',
      },
      info: {
        main: colors.accent.info,
      },
      success: {
        main: colors.primary.main,
      },
    },
    typography: {
      fontFamily: [
        'Inter',
        'Poppins',
        'Roboto',
        '-apple-system',
        'BlinkMacSystemFont',
        '"Segoe UI"',
        '"Helvetica Neue"',
        'Arial',
        'sans-serif',
      ].join(','),
      h4: {
        fontWeight: 700,
        letterSpacing: '-0.02em',
      },
      h5: {
        fontWeight: 600,
        letterSpacing: '-0.01em',
      },
      h6: {
        fontWeight: 600,
        letterSpacing: '-0.01em',
      },
      button: {
        textTransform: 'none',
        fontWeight: 600,
      },
    },
    shape: {
      borderRadius: 12,
    },
    components: {
      MuiAppBar: {
        styleOverrides: {
          root: {
            backgroundColor: colors.background.paper,
            boxShadow: mode === 'dark' ? '0 1px 3px rgba(0,0,0,0.3)' : '0 1px 3px rgba(0,0,0,0.05)',
            borderBottom: `1px solid ${mode === 'dark' ? '#2A2A2A' : colors.secondary.light}`,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            boxShadow: mode === 'dark' ? '0 2px 8px rgba(0,0,0,0.3)' : '0 2px 8px rgba(0,0,0,0.06)',
            borderRadius: 12,
            border: `1px solid ${mode === 'dark' ? '#2A2A2A' : colors.secondary.light}`,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': {
              boxShadow: mode === 'dark' ? '0 4px 16px rgba(38, 166, 154, 0.25)' : '0 4px 16px rgba(0, 150, 136, 0.15)',
              transform: 'translateY(-2px)',
            },
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            padding: '10px 24px',
            fontWeight: 600,
            textTransform: 'none',
            boxShadow: 'none',
            transition: 'all 0.2s ease',
          },
          contained: {
            backgroundColor: colors.primary.main,
            color: '#FFFFFF',
            '&:hover': {
              backgroundColor: colors.primary.dark,
              boxShadow: mode === 'dark' ? '0 4px 12px rgba(38, 166, 154, 0.4)' : '0 4px 12px rgba(0, 150, 136, 0.3)',
            },
          },
          outlined: {
            borderColor: colors.primary.main,
            color: colors.primary.main,
            '&:hover': {
              borderColor: colors.primary.dark,
              backgroundColor: mode === 'dark' ? 'rgba(38, 166, 154, 0.15)' : 'rgba(0, 150, 136, 0.08)',
            },
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: 'none',
            fontWeight: 500,
            fontSize: '0.95rem',
            minHeight: 48,
            borderRadius: 8,
            marginRight: 1,
            transition: 'all 0.2s ease',
            '&.Mui-selected': {
              color: colors.primary.main,
              backgroundColor: mode === 'dark' ? 'rgba(38, 166, 154, 0.15)' : 'rgba(0, 150, 136, 0.1)',
              fontWeight: 600,
            },
            '&:hover': {
              backgroundColor: mode === 'dark' ? 'rgba(38, 166, 154, 0.1)' : 'rgba(0, 150, 136, 0.05)',
              color: colors.primary.main,
            },
          },
        },
      },
      MuiTabs: {
        styleOverrides: {
          indicator: {
            backgroundColor: colors.primary.main,
            height: 3,
            borderRadius: '3px 3px 0 0',
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            fontWeight: 500,
          },
        },
      },
      MuiTextField: {
        styleOverrides: {
          root: {
            '& .MuiOutlinedInput-root': {
              borderRadius: 10,
              '&:hover fieldset': {
                borderColor: colors.primary.main,
              },
              '&.Mui-focused fieldset': {
                borderColor: colors.primary.main,
              },
            },
          },
        },
      },
    },
  });
};

// Default theme (light mode)
export const theme = getTheme('light');
export { getTheme };

