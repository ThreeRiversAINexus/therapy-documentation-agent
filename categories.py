def get_categories():
    """Return list of therapy documentation categories"""
    return [
        {
            "id": "journaling",
            "name": "Journaling (Counting entries / Cognitive therapy)"
        },
        {
            "id": "sleep",
            "name": "Sleep (Fitbit data / Dreaming)"
        },
        {
            "id": "physical",
            "name": "Physical Activity (Fitbit HR / Steps)"
        },
        {
            "id": "meditation",
            "name": "Meditation (Apple Health / Calm)"
        },
        {
            "id": "productivity",
            "name": "Productivity & Work (Cold Turkey / iOS Screen Time)"
        },
        {
            "id": "spiritual",
            "name": "Spiritual Practice (Solo practice / Group events)"
        },
        {
            "id": "self_care",
            "name": "Basic Self-Care (Meals, hygiene, meds / Budget / Appts)"
        }
    ]
