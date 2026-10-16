# TypeScript 타입 예

TypeScript 전용 절의 규칙별 코드 예. 바탕 원칙은 언어 공통: principle-type-system-discipline, principle-boundary-discipline

## 브랜드 타입

- 원시 타입에 브랜드를 붙여 서로 섞이지 않게 구분. 경계에서 한 번 검증하고 그 뒤 코드는 타입 신뢰
- `readonly __brand: 'X'` 모양 유지. 새 관례 금지

```ts
type AgentId = string & { readonly __brand: 'AgentId' };

class AgentIdError extends Error {
  constructor(input: string) {
    super(`invalid agent id: ${input}`);
    this.name = 'AgentIdError';
  }
}

function parseAgentId(input: string): AgentId {
  if (!isUuid(input)) throw new AgentIdError(input);
  return input as AgentId;
}

function focusAgent(id: AgentId): void {
  /* input is trusted */
}
```

## 판별 유니온

- 변형은 리터럴 판별자로 모델링. 모든 변형이 같은 필드 이름을 공유하고 값이 변형마다 고유해서 불가능한 조합 표현 불가
- 판별자 이름 하나(`kind`, `type`, `tag`) 선택 후 유지

```ts
// Don't. Boolean + optionals lets contradictory states exist.
type DiffState = { loading: boolean; diff?: GitDiff; error?: string };

// Do. Only valid states exist.
type DiffState =
  | { kind: 'loading' }
  | { kind: 'ready'; diff: GitDiff }
  | { kind: 'error'; error: string };
```

## 구성적 모델링

- 느슨한 타입을 런타임 검사로 제한하는 대신 모두 유효한 부품으로 타입 구성

비어 있지 않음, 가변 길이 튜플:

```ts
type NonEmpty<T> = [T, ...T[]];

// Don't: T[] plus a length check every caller must repeat
function pickWinner(entries: string[]): string {
  if (entries.length === 0) throw new EmptyEntriesError();
  return entries[Math.floor(Math.random() * entries.length)];
}

// Do: an empty value of the type can't exist
function pickWinner(entries: NonEmpty<string>): string {
  return entries[Math.floor(Math.random() * entries.length)];
}
```

- 평범한 `T[]`가 들어오는 곳에서 가드로 한 번 좁히기. 그 뒤로는 타입이 사실을 전달

```ts
const isNonEmpty = <T>(items: T[]): items is NonEmpty<T> => items.length > 0;
```

짝수 길이, 쌍:

```ts
type Pairs<T> = [T, T][];
```

시간 범위, 시작과 길이:

```ts
// Don't: a comment holds the invariant
type TimeRange = { start: Date; end: Date }; // start <= end

// Do: a negative range can't be written; derive end when needed
type TimeRange = { start: Date; durationMs: number };
```

- `durationMs`는 평범한 숫자. 길이 자리에 아무 숫자나 넘어올 수 있을 때만 브랜드 추가, 습관적 브랜드 금지
- 나쁜 상태를 만들 수 없는 표현 선택 후 필요한 형태의 읽기 헬퍼 제공(`pairs.flat()`, `rangeEnd()`)

## 모든 입력을 처리하는(total) 가장 단순한 타입

- 모든 타입 강화 금지. 그 타입을 쓰는 모든 연산이 모든 입력을 처리하면 `T[]` 유지

```ts
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0); // [] is 0, fine
```

- 느슨한 타입 때문에 쓰는 곳에서 사실과 다른 단언이 필요할 때만 강화. 신호: `!`, `arr[0] as T`, "일어날 리 없음" throw

```ts
// Don't: partiality smuggled past the compiler
function newestSession(sessions: Session[]): Session {
  return sessions.at(0)!;
}

// Do: strengthen the input; the assertion disappears
function newestSession(sessions: NonEmpty<Session>): Session {
  return sessions[0];
}
```

- 결과를 `Session | undefined`로 약하게 하는 방법도 모든 입력을 처리하는 시그니처

## `any`보다 `unknown`

- 외부 데이터는 언제나 `unknown`. 쓰기 전에 좁히기
- 외부 출처: RPC 페이로드, `JSON.parse`, `postMessage`, IPC, 파일 내용, 환경 변수, 데이터베이스 결과

```ts
// Don't
function handle(input: any) {
  return input.foo.bar;
}

// Do
function handle(input: unknown) {
  if (typeof input === 'object' && input !== null && 'foo' in input) {
    // narrowed; compiler verifies access
  }
}
```

## 손으로 쓴 가드보다 스키마

- 외부 데이터의 속성별 타입 가드 작성 전 저장소의 런타임 스키마 라이브러리와 기존 스키마 확인
- 스키마 하나가 검증 소유, TypeScript 타입은 스키마에서 도출. 서로 어긋날 수 있는 스키마·중복 인터페이스·가드 병행 금지

```ts
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(['admin', 'member']),
});

type User = z.infer<typeof UserSchema>;

function parseUser(input: unknown): User {
  return UserSchema.parse(input);
}
```

- 실패가 예상되는 분기는 `safeParse`. 다른 스키마 라이브러리를 쓰는 저장소는 그 라이브러리의 같은 추론 헬퍼
- 가드 하나를 위한 새 스키마 의존성 추가 금지. 코드베이스가 이미 쓰는 스키마 체계 우선

## `as` 캐스트 금지

- 모든 `as`는 언젠가 터질 수 있는 런타임 오류. 타입 시스템이 주장을 확인한 뒤에만 캐스트

```ts
import { z } from 'zod';

// Don't
const user = data as User;

// Don't
function isUser(data: unknown): data is User {
  return typeof data === 'object' && data !== null && 'id' in data;
}

// Do
const userSchema = z.object({ id: z.string(), name: z.string() });
type User = z.infer<typeof userSchema>;

function parseUser(data: unknown): User {
  return userSchema.parse(data);
}
```

- 타입이 먼저 있으면 검증기에 그 타입 표기. 타입보다 덜 증명하는 검증기는 컴파일 오류(아래에서 `name` 삭제 시 대입 실패)

```ts
type User = { id: string; name: string };

const userSchema: z.ZodType<User> = z.object({ id: z.string(), name: z.string() });
```

기존 `as` 제거 때 추론 실패 원인 → 처리:

- 판별자 없음 → 판별자 추가, 판별 유니온으로 변경
- 지나치게 넓은 원본 타입(예: `Record<string, unknown>`) → 좁히기
- 타입 없는 경계 → 그 모양을 소유한 스키마로 파싱. 스키마가 없는 곳에만 추가
- 정말 표현 불가 → 브랜드 타입이나 `satisfies`

## 좁히기 위계

가장 좋은 것부터 최후 수단까지:

1. 판별 유니온 switch·if. 컴파일러의 자동 좁히기
2. `in` 연산자. `'key' in obj`는 그 키를 가진 변형으로 좁히기
3. `typeof`·`instanceof`. 원시 타입과 클래스 인스턴스
4. 사용자 정의 타입 가드. 위의 방법으로 모자랄 때
5. `as` 캐스트. 검증한 뒤에만

```ts
function area(s: Shape): number {
  if ('radius' in s) return Math.PI * s.radius ** 2; // narrowed to circle
  return s.width * s.height; // narrowed to rect
}
```

## 타입 가드

- 가드는 주장을 실제로 확인. 거짓 가드는 안전해 보이는 이름 뒤에 버그를 숨겨서 `as`보다 나쁜 선택
- 가능하면 판별자로 좁히기 우선

```ts
function isCircle(s: Shape): s is Shape & { kind: 'circle' } {
  return s.kind === 'circle';
}
```

## 빠짐없음 검사

- default 분기에서 판별 대상을 `never` 타입 지역 변수에 대입
- 값을 돌려주는 switch는 return 방식, 문장 switch는 void 방식

```ts
// Value-returning switch
function area(s: Shape): number {
  switch (s.kind) {
    case 'circle':
      return Math.PI * s.radius ** 2;
    case 'rect':
      return s.width * s.height;
    default: {
      const unreachable: never = s;
      return unreachable;
    }
  }
}

// Void switch
function handle(s: Shape): void {
  switch (s.kind) {
    case 'circle':
      drawCircle(s);
      break;
    case 'rect':
      drawRect(s);
      break;
    default: {
      const unreachable: never = s;
      void unreachable;
    }
  }
}
```

## `as`보다 `satisfies`

- `satisfies`는 리터럴 타입을 넓히지 않는 검증

```ts
// Don't. Widens, loses literal types.
const config = { theme: 'dark', cols: 3 } as Config;

// Do. Validates AND preserves literal types.
const config = { theme: 'dark', cols: 3 } satisfies Config;
// config.theme is 'dark' (literal), not string
```

## 경계 검증

- 데이터가 들어오는 곳에서 한 번 검증, 안에서는 타입 신뢰
- 전송 형식(proto, JSON-RPC): 상위 호환 변경이 옛 클라이언트를 깨지 않도록 `ignoreUnknownFields`로 파싱
- 저장된 JSON: 버전 정보를 붙여 저장, 파싱 실패 처리
- 호출 사슬 깊은 곳의 재검증 금지

## 스키마에서 도출한 타입

- `.proto`, OpenAPI 명세, GraphQL 스키마, 데이터베이스 마이그레이션이 모양을 정의하면 생성된 타입에서 도출. 중복 정의 금지
- 새 인터페이스 작성 전 `Pick`, `Omit`, `Parameters`, `ReturnType`, `Awaited`, `typeof` 우선

```ts
// Don't. Duplicate shape, drifts when the schema changes.
type CheckSummary = {
  totalCount: number;
  checks: { name: string; status: string }[];
};
function renderChecks(s: CheckSummary) {
  /* ... */
}

// Do. Derive from the generated schema type.
import type { ChecksMessage } from '<generated module>';
function renderChecks(s: Pick<ChecksMessage, 'totalCount' | 'checks'>) {
  /* ... */
}
```

## 객체 인자

- 핫 패스 제외: 프레임마다 렌더, 토크나이저, 파서, 할당 비용이 중요한 촘촘한 루프

```ts
// Don't. Swap two args, still compiles.
openFile(uri, {
  startLineNumber: 10,
  startColumn: 1,
  endLineNumber: 10,
  endColumn: 1,
});

// Do. Order-independent, self-documenting.
openFile({
  uri,
  selection: {
    startLineNumber: 10,
    startColumn: 1,
    endLineNumber: 10,
    endColumn: 1,
  },
});
```
