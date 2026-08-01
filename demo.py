"""Walk through a full meeting session without Telegram, a database or an API key.

The bot's real job is running a council meeting: an admin opens a session, members join
with a code and a password, everyone votes on each agenda item, and the bot produces the
protocol. This script replays that flow against the same helper functions the bot uses.
"""

import random
import string

from bot.common.infinitiveConverter import convert_to_infinitive

AGENDA = [
    "Про затвердження програми розвитку молоді",
    "Про створення робочої групи",
    "Про припинення повноважень члена ради",
    "Про оголошення конкурсу проєктів",
]

PARTICIPANTS = ["Коваль О. І.", "Мельник Д. С.", "Ткаченко І. П.", "Бондар Л. В.", "Шевчук Н. О."]

VOTES = [
    {"for": 5, "against": 0, "abstain": 0, "not_voted": 0},
    {"for": 4, "against": 1, "abstain": 0, "not_voted": 0},
    {"for": 3, "against": 0, "abstain": 2, "not_voted": 0},
    {"for": 5, "against": 0, "abstain": 0, "not_voted": 0},
]


def session_credentials():
    """The bot generates a join code and a password when a session is created."""
    code = "".join(random.choices(string.digits, k=6))
    password = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return code, password


def main():
    code, password = session_credentials()

    print("=" * 78)
    print("1. The admin creates a session")
    print("=" * 78)
    print(f"   Session code: {code}")
    print(f"   Password:     {password}")
    print("   These are shared with the council members, who join from their own Telegram.\n")

    print("=" * 78)
    print("2. Members join")
    print("=" * 78)
    for name in PARTICIPANTS:
        print(f"   joined: {name}")
    print(f"   {len(PARTICIPANTS)} participants registered for the attendance appendix.\n")

    print("=" * 78)
    print("3. Voting, one agenda item at a time")
    print("=" * 78)
    for index, (item, result) in enumerate(zip(AGENDA, VOTES), start=1):
        print(f"   Item {index}: {item}")
        print(
            f"      for {result['for']} · against {result['against']} · "
            f"abstained {result['abstain']} · did not vote {result['not_voted']}"
        )
    print()

    print("=" * 78)
    print("4. The protocol is written in the wording the paperwork requires")
    print("=" * 78)
    print(f"   {'Agenda item (as submitted)':<48}{'Protocol wording (decision)'}")
    print("   " + "-" * 75)
    for item in AGENDA:
        print(f"   {item:<48}{convert_to_infinitive(item)}")
    print()
    print("   The bot then emits two DOCX files:")
    print("     · Протокол №N            - decisions and vote tallies per item")
    print("     · Додаток присутності    - the signed attendance sheet")


if __name__ == "__main__":
    main()
