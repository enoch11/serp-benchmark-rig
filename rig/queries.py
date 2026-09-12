"""Fixed query set — 5 difficulty classes x 4 queries. Same strings every wave."""

QUERY_SET = [
    # navigational
    ("navigational", "apple inc"),
    ("navigational", "github"),
    ("navigational", "minnesota department of health"),
    ("navigational", "smashing magazine"),
    # informational short
    ("informational_short", "weather minneapolis"),
    ("informational_short", "how tall is everest"),
    ("informational_short", "python string split"),
    ("informational_short", "what time is it in japan"),
    # local
    ("local", "coffee shop 55401"),
    ("local", "hardware store near me"),
    ("local", "plumber 55404"),
    ("local", "minneapolis tattoo shops"),
    # long-tail question
    ("longtail_question", "can you file taxes late without a penalty"),
    ("longtail_question", "how long does a bank transfer take"),
    ("longtail_question", "why is my mac fan so loud"),
    ("longtail_question", "does cold weather kill car batteries"),
    # shopping / commercial
    ("shopping", "best noise cancelling headphones under 200"),
    ("shopping", "standing desk under 400"),
    ("shopping", "best running shoes for flat feet"),
    ("shopping", "macbook air m3 price"),
]

CLASSES = ["navigational", "informational_short", "local", "longtail_question", "shopping"]
