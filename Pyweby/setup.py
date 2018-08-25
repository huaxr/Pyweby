# coding=utf-8
from setuptools import setup
'''
把redis服务打包成C:\Python27\Scripts下的exe文件
'''

setup(
    name="Pyweby",
    version="1.0",
    author="huaxr",
    author_email="787518771@qq.com",
    description=("Very Sexy Web Framework. savvy?"),
    license="GPLv3",
    keywords="redis subscripe",
    url="https://github.com/huaxr/Pyweby",

    install_requires=[
        'pymysql',
        'concurrent',
        'redis>=2.10.5',
    ],

    # 添加这个选项，在windows下Python目录的scripts下生成exe文件
    # 注意：模块与函数之间是冒号:
    entry_points={'console_scripts': [
        'redis_run = DrQueue.RedisRun.redis_run:main',
    ]},

    # long_description=read('README.md'),
    classifiers=[  # 程序的所属分类列表
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: GNU General Public License (GPL)",
    ],
    # 此项需要，否则卸载时报windows error
    zip_safe=False
)