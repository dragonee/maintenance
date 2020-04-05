
import getpass

def input_until_valid(
    prompt,
    message,
    check=lambda x: x != '',
    default=None,
    default_prompt="{prompt} [{default}]: "
):
    if default:
        prompt = default_prompt.format(
            prompt=prompt.strip(': '),
            default=default,
        )

    while True:
        s = input(prompt)

        if s == '' and default:
            s = default

        if check(s):
            return s

        print(message)


def getpass_until_valid(
    prompt,
    message,
    check=lambda x: x != '',
    default=None,
    default_prompt="{prompt} [*****]: "
):
    if default:
        prompt = default_prompt.format(
            prompt=prompt.strip(': ')
        )

    while True:
        s = getpass.getpass(prompt)

        if s == '' and default:
            s = default

        if check(s):
            return s

        print(message)


def getpass_twice_until_valid(
    prompt,
    message,
    check=lambda x: x != '',
    repeat="{prompt} (again): ",
    mismatch_message="Passwords need to match.",
    default=None,
    default_prompt="{prompt} [*****]: "
):
    if default:
        prompt = default_prompt.format(
            prompt=prompt.strip(': ')
        )

    while True:
        s = getpass.getpass(prompt)

        if s == '' and default:
            s = r = default
        else:
            r = getpass.getpass(repeat.format(prompt=prompt.strip(': ')))

        if s != r:
            print(mismatch_message)

        if check(s):
            return s

        print(message)

def ask_for(words, no_words=None, case_sensitive=True):
    if no_words:
        prompt = "[{}/{}] ".format(words[0], no_words[0])
    else:
        prompt = "[{}] ".format(words[0])

    if case_sensitive:
        match = lambda x, y: x == y
    else:
        match = lambda x, y: x.lower() == y.lower()

    while True:
        s = input(prompt)

        for word in words:
            if match(word, s):
                return True

        if no_words is None:
            return False

        for word in no_words:
            if match(word, s):
                return False
