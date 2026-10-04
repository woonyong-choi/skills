"""파일 내용을 출력한다.

인자: 파일 하나
출력: stdout 파일 내용, 종료 0
"""
import sys

# cost: time O(n), heap O(n), stack O(1)
# cost: io 2
# vars: n = 파일 크기
# vars: d = 참조 깊이
# basis: estimate
def main():
    with open(sys.argv[1]) as source:
        print(source.read())

if __name__ == '__main__':
    main()
