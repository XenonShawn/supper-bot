# README: NUS Orbital 2022

## Team Name

SupperFarFetch

## Proposed Level of Achievement

Project Gemini

## Motivation

Consolidating supper orders is difficult. One common way is to send a message to a channel declaring that one is opening
up orders for supper. To add in their orders, people copy the current message, add in their own order, and then send it
back to the group.

However, this method brings about many issues. People keep changing their minds, causing long chains of messages that 
disrupt the flow of the conversation of the group. There is a high chance that someone might accidentally overwrite
another person's order, causing conflict in the end. Tracking payment is an issue as well; people can forget to pay the
supper host the cost of their meal.

Introducing: The SupperFarFetch bot! This Telegram bot will assist in creating a supper jio through a setup process in
DMs. The created jio can then be shared to as many groups as the host wishes. Users can then add in their orders through
DMing the bot. This way, chat groups will not be spammed, and people's orders can't be accidentally forgotten!

You can test the bot here: https://t.me/supperfarfetch_bot

## Aim

To make consolidation of supper orders simple.

## User Stories

As a host, I want to
* quickly set up a supper jio.
* easily share the supper jio with multiple groups.
* have a clear list of items to be ordered.
* be able to close the jio so that no one can modify their orders.
* be able to see who have declared that they have paid.
* easily remind users to pay for their meal.

As a user, I want to
* be able to add in my food orders.
* be able to delete my food orders.
* indicate that I have paid.
* set items as favourite.
* quickly add favourite items to a supper jio.
* be able to amend my favourite items.

## Features and Timeline

Since group chats are often hosted on Telegram, a Telegram bot is most suitable for this project.

### Milestone 1

* Research on problem statement and think of how to best solve the issue
* Research on `python-telegram-bot` Python library
* Implement skeleton (folder structure) of the Telegram Bot
* Implement proof of concept - Ability to create a supper jio and share it to groups

Technical proof of concept: https://drive.google.com/file/d/1WwHLL6n0Hp4cOG9htfqiI0GriNW-8Ciw/view?usp=sharing

### Milestone 2

* Structure changes
  * Created a `db` submodule for all the database related classes and functions
  * Refactored common functions into a separate module, `supperbot.commands.helper`
* Core features implemented
   * Supper jio creation process through DMs
     * Host can indicate extra information (eg minimum order, any discounts, order location, cut off timing)
     * Host can close the supper jio here as well
     * The supper jio can then be shared to any group
   * Individuals are able to add and delete their own orders
   * Produce final ordering list 
   * Users can indicate that they have paid
* Quality of Life features implemented
  * "Put Message Below" button - sends the order message to the bottom of the chat

### Milestone 3
* Structure and backend changes
  * Created `Procfile` for deployment to Heroku
  * Added `psycopg2` as a dependency so that SQLAlchemy can connect to Heroku Postgres
* Core features implemented
  * Allow host to ping users who have yet to pay for their food
  * Allow users to view the supper jios they created
  * Allow users to view the supper jios they have pariticpated in
* Quality of life features implemented
  * Favourite orders
    * Adding of favourite items through the add orders interface
    * Showing of favourite items when adding items to a Supper Jio
    * Deleting of favourite items through the add orders interface
    * Deleting of favourite items through the main menu
  * Edit description of Jio
  * Minor changes to user interface based on feedback from mass testing
    * Renaming buttons to be more descriptive
    * Changed the `InlineQuery` so that users cannot hijack another supper jio

### Further Possible Improvements

* Allow host to automatically ping users every 24 hours
* Allow combination of orders in the final ordering list
* Allow host to specify it's not a "Supper" jio - this bot can be used for tea breaks or meals as well
* Left/Right buttons so that the user can view more than 50 of their past jios

## Testing

As a Telegram Bot does not easily lend itself to unit testing, we instead did minor testing on the developers' end, as
well as mass testing with a Residential College in NUS. Bugs found (see issues section below) were fixed as soon as 
possible, and feedback was taken into account when making minor changes to the user interface.

## Tech Stack

1. Python
2. `python-telegram-bot` to interface with the Telegram API. v20 is used despite being a pre-release, as it supports 
   `asyncio`.
3. Heroku will be the hosting solution, using their provided Heroku Postgres for storage.
4. `SQLAlchemy` ORM is used to manage the database, as it allows for a smoother transition to Heroku Postgres during
    deployment.

## Software Development Practices

### Code Style (Black)

_Black_ is a PEP 8 compliant opinionated Python code formatter, which allows for a consistent code style across
different programmers. Black is used as it is widely utilized in the community (eg `requests`, `SQLAlchemy` and 
`Django`). Furthermore, it analyzes the code it formats to ensure that the reformatted code produces the same Abstact
Syntax Tree, which ensures correctness of the code.

### Refactoring

Refactoring was frequently done to improve the quality of code after the initial writing of the code. For example,
frequently used functions were shifted to `supperbot/commands/helper.py`. Further refactoring will be done after 
Milestone 3 to improve on the quality of the codebase after more features are added.

### Version Control

Git is used to track the history of all changes made and to help recover from mistakes. It also allows multiple users to
work on the same piece of code on the same time. Github is used as the Git server. Majority of the commits were made by
one the team members, while the other team member focused more on the user experience and testing, as well as the design
and creation of the posters and videos.

The code of the bot can be viewed here: https://github.com/XenonShawn/Orbital22

## Issues Faced During Development

### Telegram API Limitations

Telegram provides two ways to guide user input:
* `InlineKeyboardMarkup`, which are buttons under a specific message, and;
* `ReplyKeyboardMarkup`, which is placed above the user's keyboard.

`InlineKeyboardMarkup` works by sending data straight to the bot, while `ReplyKeyboardMarkup` causes a text message to
be sent instead. The two have their uses in certain scenarios, but Telegram does allow both to be set on the same
message.

This resulted in poorer user experience - when asking for the name of the restaurant for a newly created supper jio,
McDonalds and Al Amaans are provided as `ReplyKeyboardMarkup` buttons since `ReplyKeybardMarkup` buttons would send a
message. This allows for code reuse for when the user types in the name of another restaurant (a message is sent).
However, this also prevents a "Cancel" button from being present as a `InlineKeyboardMarkup` attached to the jio
message, as Telegram API does not allow it.

The "Cancel" button is placed as a button in the `ReplyKeyboardMarkup` instead, which may not always be visible as
Reply Keyboards may be hidden by default on certain Telegram clients. User experience is thus affected.

### Time-Based Bugs

Some bugs also only popped up after a few days. For example, you cannot edit messages once they have been sent more than
two days ago. This means that if a user were to try to use old messages, it might not be able to work. Try except blocks
had to be used whenever the `edit_message` method was used.

### `python-telegram-bot` Library Limitations

The ptb library provides a convenient handler to help maintain "conversations" - `ConversationHandler`. This handler
assists the programmer by handling state - allowing the programmer to seamlessly program situations where you need to
obtain information sequentially (eg name, then occupation, then a question based on provided occupation).

However, it is possible for multiple `ConversationHandler`s to be active at the same time. In the case of the supper
bot, `ConversationHandler`s are used for (in particular) creating a new supper jio, editing a description and adding
a new order to a jio. All these functionalities require the user to type in an input. If all `ConversationHandler`s were
active, then the resolution of which functionality would be activated when a user sends an input depends on which
handler is added to the bot first.

This situation is easy to replicate - a user just has to try to add an order to an existing jio, and without typing a 
new order, try to create a new supper jio. This results in two `ConversationHandler`s being active.

This issue is not easily solved, and is hence currently left as a "bug" in the code.

### Telegram Clients Interfering with Testing

One issue is that telegram clients would cache results (esp `InlineQueryResult`) to reduce the number of requests being
sent to the server. However, this interferes when changing the code as we would have to wait for a minute before the
telegram client actually sends a new request to the bot. This was particularly frustrating when editing the
`InlineQueryResult` code used in sharing jios to other group chats.

This issue actually presents an unsolvable bug - if the user were to share a jio, then edit the description of the jio,
and tries to share the jio again, the newly shared jio will have the old description (at least until someone adds in an 
order which updates the message) due to the Telegram client caching the result.

### Mass Testing

Mass testing, while helpful for actual feedback, is difficult to coordinate and is time-consuming. Fixing a discovered 
bug before the testing is over might not always be possible. One of our tests involved ~15 people using the bot at the
same time, and a bug prevented some from keying in their orders. The source of the bug was not found (the bug is that it
would say "add order functionality not implemented"), but a workaround was only a found after the group has ordered 
their food.

Some feedback on user interface was also not clear, and changes had to be rolled back due to miscommunication.
