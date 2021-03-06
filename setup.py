from setuptools import find_packages, setup


def parse_requirements_file(path):
    return [line.rstrip() for line in open(path, "r")]


reqs_main = parse_requirements_file("requirements.txt")

setup(
    name="emei",
    packages=["emei"],
    description="Emei is a toolkit for developing causal reinforcement learning algorithms.",
    author="Honglong Tian",
    url="https://github.com/FrankTianTT/emei",
    author_email="franktian424@qq/com",
    license="MIT",
    version=0.1,
    python_requires=">=3.7",
    install_requires=reqs_main,
)
