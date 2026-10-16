"""파일 내용을 출력한다.

인자: 파일 하나
출력: stdout 파일 내용, 종료 0
"""
import sys

def main():
    with open(sys.argv[1]) as source:
        print(source.read())

if __name__ == '__main__':
    main()
