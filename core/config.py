import tomllib


with open('config.toml', 'rb') as fp:
    config = tomllib.load(fp)
