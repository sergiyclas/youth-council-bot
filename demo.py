"""Run the Ukrainian NLP layer without Telegram or an OpenAI key.

The bot turns agenda items written as nominalisations ("Про затвердження ...")
into the infinitive form required by meeting protocols.
"""

from bot.common.infinitiveConverter import convert_to_infinitive

AGENDA_ITEMS = [
    "Про затвердження програми розвитку молоді",
    "Про створення робочої групи",
    "Про припинення повноважень члена ради",
    "Про оголошення конкурсу проєктів",
    "Про розгляд звернення мешканців",
]


def main():
    print("Agenda item".ljust(48), "->", "Protocol wording")
    print("-" * 100)
    for item in AGENDA_ITEMS:
        print(item.ljust(48), "->", convert_to_infinitive(item))


if __name__ == "__main__":
    main()
