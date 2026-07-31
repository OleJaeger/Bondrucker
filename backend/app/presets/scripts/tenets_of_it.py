"""Liefert eine zufaellig ausgewaehlte, IT-Spruch zurück.

Bewusst ohne Emojis - die Font A des ESC/POS-Druckers unterstuetzt nur
einen begrenzten Zeichensatz.
"""

from __future__ import annotations

import random

_MESSAGES = [
    "Reboot, reinstall, replace.",
    "Rebooting is a band aid. Figure out why you had to.",
    "It's always DNS.",
    "When it's not DNS, it's MTU.",
    "When it's not MTU, it's BGP.",
    "When it's not BGP, it's LACP.",
    "Under-promise, over-deliver.",
    "Plan for the worst, hope for the best.",
    "Always implement two-factor-authentication, no matter how loudly the users complain.",
    "Have the user show you the problem, often it is the user doing something in an unusual way.",
    "Fast. Cheap. Good. You may pick one, two if you're lucky.",
    "Never stop learning.",
    "The Six Ps: Proper Planning Prevents Piss Poor Performance.",
    "It's always an emergency, until it incurs an extra charge.",
    "Everyone has a test environment, not everyone is lucky enough to have a separate production environment.",
    "If anyone can't find the documentation it's not documented, if it's not documented it doesn't exist.",
    "If you think it's going to be a disaster, get it in writing and CYA.",
    "Poor planning on a users part, does not constitute an emergency on yours.",
    "Fridays are read-only. (aka - no changes on a Friday)",
    "A backup isn't a backup until you've restored successfully from it.",
    "Snapshots are not backups.",
    "If a backup isn't off-site, it isn't a backup.",
    "If it isn't in a ticket, it's not getting done.",
    "Treat all users the same, regardless of their last name.",
    "It's never a \"5 minute thing\".",
    "Security and ease of use.. rarely walk hand in hand.",
    "Not my circus, not my monkeys.",
    "Everybody lies.",
    "Never ask a user a question that you can easily confirm yourself.",
    "The fastest path to resolution first requires removing the user from the problem. (aka isolate layer 8)",
    "You are replaceable at work, no matter how highly you think of yourself. You are not replaceable at home.",
    "Never give a web developer/designer access to the DNS.",
    "Own up to your mistakes. That way, when it isn't your fault, people will believe you.",
    "If you have to do something twice, automate it.",
    "Never spend 6 minutes doing something manually, that you spend 6 hours failing to automate.",
    "To make an error is human. To propagate an error to all servers in an automatic way is devops.",
    "Skilled IT professionals will continuously be given more work, until they can do none of it skillfully.",
    "Give me a new hire that is a blank slate and willing to learn, over a seasoned tech that hates this job and doesn't want to learn or change.",
    "IT time is relative.",
    "Yes it's free/cheap. No, it's not going in the server room.",
    "You provide the problem and business case, let IT provide the solution.",
    "IT's job is to solve people problems with technology.",
    "Technology can't solve people problems.",
    "Nothing is more permanent than a temporary expedient.",
    "Fix the problem now, it's just going to happen again when it's less convenient.",
    "If the network guys say it's not the network, there is an 80% chance it's the network.",
    "Traceroute is your friend.",
    "80% of the time CAPEX becomes OPEX when you can get 0% financing. Accounting HATES CAPEX.",
    "If it doesn't log automatically make it log! Log's just spit out the answer for you!",
    "There are some jobs and clients you must walk away from.",
    "If you can smell the magic smoke, you're already screwed.",
    "\"Working just fine\" and \"too screwed to log an error\" look an awful lot alike.",
    "The longer everything goes according to plan, the bigger the impending disaster.",
    "Sales Engineers are a gift from heaven, they prevent salespeople from over-promising.",
    "Printers have moods, most of the time that mood is 'Fuck you'.",
]


def generate() -> str:
    return random.choice(_MESSAGES)
