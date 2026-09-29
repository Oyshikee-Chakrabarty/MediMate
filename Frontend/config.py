"""Shared design tokens for the Milestone 1+2 demo UI.

Every color / size decision lives here so restyling never means hunting
through widget code. Same idea as the main app's `app/config.py`.
"""

# ---- theme colors ----------------------------------------------------- #
GREEN: str = "#72C040"          # patient theme (PNG 3)
ORANGE: str = "#F36B20"         # caretaker theme (PNG 4)
AMBER: str = "#F36B20"          # caretaker alias for backwards compatibility
BLUE: str = "#1E6FF4"           # primary blue (PNG 1 & 2 buttons)
CYAN: str = "#0096D6"           # bottom nav and progress cyan (PNG 3, 4, 5)
CYAN_BG: str = "#80E0F8"        # auth bubble header background
INPUT_BG: str = "#D2F4FD"       # input background pills (PNG 1, 2, 6)
INPUT_TEXT: str = "#0F3D6E"     # input text color
TITLE_NAVY: str = "#0A3663"     # bold headers (PNG 1, 2, 3, 4, 5, 6)
SCHEDULE_NAVY: str = "#0B3566"  # schedule card dark blue
CARD_BG_BLUE: str = "#E0F5FE"   # medicine card light blue
CARD_BORDER_BLUE: str = "#BCE5F9"
CARD_BG_GREEN: str = "#D4EDDA"  # medicine list card soft green (PNG 5)
RED: str = "#EF4444"            # alert / missed dose red
TAKEN_GREEN: str = "#81D883"    # adherence taken green pill
YELLOW: str = "#FFCA28"         # progress bar yellow
TEXT: str = "#2C3E50"           # primary body text
MUTED: str = "#7A8A9E"          # subtitles and labels
WHITE: str = "#FFFFFF"

# ---- sizing ------------------------------------------------------------ #
APP_WIDTH: int = 420
FIELD_WIDTH: int = 340
CARD_WIDTH: int = 380
BUTTON_HEIGHT: int = 50
FONT: int = 16                  # healthcare apps: readable, never tiny
