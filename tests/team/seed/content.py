"""Team test scenario: the support desk of Butter & Bean, a gaming cafe in Islamabad.

All people, e-mail addresses and tickets are synthetic test data. The .example
domain is reserved for documentation and tests, so no mail can reach anyone.
The API tests and the Playwright tests both import their data from here.
"""

PASSWORD = "Pa33w0rd"  # same test password as the upstream demo accounts
DOMAIN = "butterbean.example"

# (username, first name, last name, role in the cafe). All staff, none superuser.
STAFF = [
    ("afnan", "Afnan", "Hussain", "Cafe manager"),
    ("arooj", "Arooj", "Abrar", "Tech lead"),
    ("rayyan", "Rayyan", "Masroor", "Barista"),
    ("haider", "Haider", "Ali", "Gaming lounge attendant"),
]
W1_STAFF = "afnan"     # logs tickets for customers (UC-2, Member 1)
W2_STAFF = "arooj"     # resolves tickets (UC-3, Member 2)
OWNER = "rayyan"       # assigned as case owner in UC-2 A1
LIMITED_STAFF = "haider"  # staff without user-management rights (AC-06)

# Customers with a login (not staff).
CUSTOMER = ("baidar", "Baidar", "Hussain")
SECOND_CUSTOMER = ("naheed", "Naheed", "Baidar")
CUSTOMER_EMAIL = f"baidar.hussain@{DOMAIN}"
SECOND_CUSTOMER_EMAIL = f"naheed.baidar@{DOMAIN}"

# (title, slug, e-mail address). Every queue accepts public submissions.
QUEUES = [
    ("Cafe Wi-Fi", "WIFI", f"wifi@{DOMAIN}"),
    ("Gaming Lounge", "LOUNGE", f"lounge@{DOMAIN}"),
    ("Ordering App", "APP", f"app@{DOMAIN}"),
    ("Kitchen and Equipment", "KITCHEN", f"kitchen@{DOMAIN}"),
]
MAIN_QUEUE = "Cafe Wi-Fi"
MAIN_QUEUE_SLUG = "WIFI"

# Sample tickets so the desk looks lived in:
# (queue slug, title, description, submitter, assigned staff, status, priority)
TICKETS = [
    ("WIFI", "Wi-Fi dies every time someone starts a match",
     "Whole lounge drops off the Wi-Fi the second a ranked match starts. Happens every evening.",
     CUSTOMER_EMAIL, "arooj", 1, 2),
    ("WIFI", "Internet super slow at the F-7 branch",
     "Pages take forever to load, speed test shows under 1 Mbps around 6 pm.",
     SECOND_CUSTOMER_EMAIL, "arooj", 1, 3),
    ("APP", "Ordering app stuck on the loading screen again",
     "Tried to order a caramel latte, the app just spins. Had to order at the counter.",
     CUSTOMER_EMAIL, "afnan", 3, 3),
    ("APP", "App takes ages to show my loyalty points",
     "Points page loads for almost a minute before anything shows up.",
     SECOND_CUSTOMER_EMAIL, "afnan", 1, 4),
    ("LOUNGE", "PC 4 in the lounge lags in every game",
     "Frame drops and input lag on PC 4, other PCs are fine.",
     CUSTOMER_EMAIL, "haider", 2, 2),
    ("LOUNGE", "Controller on station 2 will not charge",
     "Left it on the dock for an hour, still at 5 percent.",
     SECOND_CUSTOMER_EMAIL, "haider", 4, 4),
    ("KITCHEN", "Espresso machine making a weird grinding noise",
     "Started this morning at the Blue Area branch. Coffee still comes out but it sounds bad.",
     f"rayyan@{DOMAIN}", "rayyan", 1, 2),
    ("WIFI", "Biscuit chewed the router cable again",
     "Our golden retriever got to the cable behind the counter. Wi-Fi down at the counter till fixed.",
     f"afnan@{DOMAIN}", "arooj", 3, 1),
]
