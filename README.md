# Bot Clown

![_](https://img.shields.io/badge/license-wtfpl-green)

![_](https://img.shields.io/badge/powered-python-yellow)


>Made by order from the Kwork exchange

Regger checks the message, then checks it for a suitable regular expression

## Tech

| Lib                    | PyPi                                            |
|------------------------|-------------------------------------------------|
| PyTelegramBotApi 4.7.1 | https://pypi.org/project/pyTelegramBotAPI/4.7.1 |
| peewee 3.15.3          | https://pypi.org/project/peewee/3.15.3          |


## Running

The bot comes without a filled database

Add your token in config.json

```commandline
git clone https://github.com/Navnica/bot-regger.git
cd bot-clown
pip3 install -r requirements.txt
python3 main.py
```

If at Windows you get `python3.exe command not found` try to use `python` instead `python3`


## Features

The sample add command 

`regex(regex) [command]('answer_text', [optional args])`

### Excamples
`regex((?:cat|dog)) answer('we dont talk here about cats or dogs')` - just reply to message

`regex((?:cat|dog)) answer_delete_after('we dont talk here about cats or dogs', 5)` - reply to message, delete before 5 seconds

`regex((?:fox)) answer_question_yes_no('Ваш вопрос о лисах?', 7)` - reply to message with inline keyboard.
