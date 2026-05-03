"""
ctv-main
简单处理一下用户侧调用

ctv - main 调用说明:

用法:
  ctv -c <路径>           读取指定 JSON 配置文件, 并生成视频
  ctv -e [保存路径]        生成示例配置文件(默认保存到 ./example_config.json)
  ctv -h                  显示帮助信息

参数说明:
  --config, -c    配置文件的 JSON 路径(字符串)
  --example, -e   生成示例配置; 可后跟保存路径, 省略则保存到当前目录下的 example_config.json (同时产生示例背景)
  --help, -h      显示本帮助

示例:
  ctv --config settings.json     # 依据配置生成视频
  ctv -e                         # 生成示例配置到当前目录
  ctv -e ./tmp/                  # 生成示例配置到指定目录

更细的调用 建议 import ctv
  
-ω-
"""

import argparse
import sys
from .core import Config, CTVField

def main():
    # 创建解析器
    parser = argparse.ArgumentParser(
        prog="ctv",
        description="ctv - main 调用",
        epilog="""
示例:
  %(prog)s --config settings.json      # 依据配置生成视频
  %(prog)s -e                          # 生成示例配置到当前目录
  %(prog)s -e ./tmp/                   # 生成示例配置到指定目录

更细的调用 建议 import ctv
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 可选参数: --config / -c
    parser.add_argument(
        "--config", "-c",
        metavar="PATH",
        type=str,
        help="JSON 配置文件的路径(字符串)"
    )
    
    # 可选参数: -e / --example (支持可选的保存路径)
    parser.add_argument(
        "--example", "-e",
        nargs="?",
        const="./",
        metavar="SAVE_PATH",
        help="生成示例配置文件; 可指定保存路径(目录), 省略则保存到当前目录下的 example_config.json (同时产生示例背景)"
    )
    
    args = parser.parse_args()
    
    # 互斥逻辑:至少提供 --config 或 -e 之一,并且不能同时使用
    if args.config and args.example is not None:
        print("错误: --config 和 --example 不能同时使用", file=sys.stderr)
        parser.print_usage()
        sys.exit(1)
    
    # 处理各模式
    if args.config:
        f = CTVField(Config.load(args.config))
        f.main()
    elif args.example:
        try:
            success = Config.save_example(args.example) # 失败内部会提示
            if success:
                print("默认配置已保存到:", args.example)
            else:
                print("默认配置保存失败")
        except Exception as e: # 因为内部没有完全处理好
            print(f"保存示例配置时发生错误: {e}")
            print("默认配置保存失败")
    else:
        parser.print_usage()
        sys.exit(1)
 
main()