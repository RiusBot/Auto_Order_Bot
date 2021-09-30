# Usage instructions
[Auto Order Bot 使用文件](https://zircon-lemonade-940.notion.site/Auto-Order-Bot-6c0666ad394f4855923f8c05f73bdae8)


# Development

### environment setup
```
make-init
```
Installs pyenv, pipenv, dev packages and requirement packages.

```
make shell
```
Activates virtualenv


### run bot
```
python src/main.py --gui
python src/gui.py
```


### pack exe

```
make compile
```

if you want to pack executable with pyinstaller for other platform, there is a way to do it with docker [document](https://github.com/cdrx/docker-pyinstaller).
Look into Makefile for more detail usage.
```
make compile-win
make compile-linux
make compile-mac
```

### TODO
1. offline history evaluation
2. parameter optimization
