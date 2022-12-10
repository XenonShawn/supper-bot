# Supper Jio Bot README

## Introduction and Motivation

Consolidating supper orders is difficult. One common way is to send a message to a channel declaring that one is opening
up orders for supper. To add in their orders, people copy the current message, add in their own order, and then send it
back to the group.

However, this method brings about many issues. People keep changing their minds, causing long chains of messages that 
disrupt the flow of the conversation of the group. There is a high chance that someone might accidentally overwrite
another person's order, causing conflict in the end. Tracking payment is an issue as well; people can forget to pay the
supper host the cost of their meal.

Introducing: The Supper Jio bot! This Telegram bot will assist in creating a supper jio through a setup process in
DMs. The created jio can then be shared to as many groups as the host wishes. Users can then add in their orders through
DMing the bot. This way, chat groups will not be spammed, and people's orders can't be accidentally forgotten!

## Features

The Supper Jio bot delivers the following features, with more to come!

For supper jio hosts,
* Creation of a supper jio, with location and additional details
* Sharing of the supper jio to possibly multiple group chats
* Closure of jios to prevent people from modifying their orders
* See a list of food to order
* See a list of people who have yet to pay
* Mass ping users who have yet to pay

For users,
* View past jios they have participated in
* Join and add orders to a jio in a group they are in
* Favourite foods for easy addition to a jio
* Declare payment for the food

Features which are planned include
* Revamping of the favourite food system to simplify it
* Pagination for past jios
* Mass sending of pictures/text from the host

## Installation 

1. Use `git clone` to clone the repository locally
2. Install the requirements (preferably in a virtual environment) as stated in requirements.txt
3. Create a `config.py`. An example config file is provided in `defaultconfig.py`.
4. Run `main.py` to start the bot.