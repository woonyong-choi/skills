# TypeScript 타입 예

[TypeScript 전용](../SKILL.md#typescript-전용) 절의 규칙별 코드 예다. 바탕 원칙은 언어 공통인 **principle-type-system-discipline** 스킬과 **principle-boundary-discipline** 스킬이다.

## 브랜드 타입

- 원시 타입에 브랜드를 붙여 서로 섞이지 않게 구분한다. 경계에서 한 번 검증하고 그 뒤 코드는 타입을 믿는다.
- `readonly __brand: 'X'` 모양을 유지한다. 새 관례를 만들지 않는다.

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

- 변형은 리터럴 판별자로 모델링한다. 모든 변형이 같은 필드 이름을 공유하고 값이 변형마다 달라서 불가능한 조합을 표현할 수 없다.
- 판별자 이름은 `kind`, `type`, `tag` 중 하나를 골라 계속 쓴다.

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

- 느슨한 타입을 런타임 검사로 제한하지 않고, 모두 유효한 부품으로 타입을 구성한다.

비어 있지 않음은 가변 길이 튜플로 쓴다.

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

- 평범한 `T[]`가 들어오는 곳에서 가드로 한 번 좁힌다. 그 뒤로는 타입이 사실을 전달한다.

```ts
const isNonEmpty = <T>(items: T[]): items is NonEmpty<T> => items.length > 0;
```

짝수 길이는 쌍으로 쓴다.

```ts
type Pairs<T> = [T, T][];
```

시간 범위는 시작과 길이로 쓴다.

```ts
// Don't: a comment holds the invariant
type TimeRange = { start: Date; end: Date }; // start <= end

// Do: derive end from duration; number still permits negative values
type TimeRange = { start: Date; durationMs: number };
```

- `durationMs`는 평범한 숫자라 음수도 허용한다. 비음수 보장은 별도 검증이 필요하다. 길이 자리에 아무 숫자나 넘어올 수 있을 때만 브랜드를 붙이고, 습관으로 브랜드를 붙이지 않는다.
- 나쁜 상태를 만들 수 없는 표현을 고른 뒤 필요한 형태의 읽기 헬퍼를 준다(`pairs.flat()`, `rangeEnd()`).

## 모든 입력을 처리하는(total) 가장 단순한 타입

- 모든 타입을 강화하지 않는다. 그 타입을 쓰는 모든 연산이 모든 입력을 처리하면 `T[]`를 유지한다.

```ts
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0); // [] is 0, fine
```

- 느슨한 타입 때문에 쓰는 곳에서 사실과 다른 단언이 필요할 때만 강화한다. 신호는 `!`, `arr[0] as T`, "일어날 리 없음" throw다.

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

- 결과를 `Session | undefined`로 약하게 하는 방법도 모든 입력을 처리하는 시그니처다.

## `any`보다 `unknown`

- 외부 데이터는 언제나 `unknown`으로 받고 쓰기 전에 좁힌다.
- 외부 출처는 RPC 페이로드, `JSON.parse`, `postMessage`, IPC, 파일 내용, 환경 변수, 데이터베이스 결과다.

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

- 외부 데이터의 속성별 타입 가드를 쓰기 전에 저장소의 런타임 스키마 라이브러리와 기존 스키마를 확인한다.
- 스키마 하나가 검증을 맡고 TypeScript 타입은 스키마에서 도출한다. 서로 어긋날 수 있는 스키마, 중복 인터페이스, 가드를 함께 두지 않는다.

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

- 실패가 예상되는 분기는 `safeParse`를 쓴다. 다른 스키마 라이브러리를 쓰는 저장소는 그 라이브러리의 같은 추론 헬퍼를 쓴다.
- 코드베이스가 이미 쓰는 스키마 체계를 먼저 쓴다.

## `as` 캐스트 금지

- 모든 `as`는 언젠가 터질 수 있는 런타임 오류다. 타입 시스템이 주장을 확인한 뒤에만 캐스트한다.

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

- 타입이 먼저 있으면 검증기에 그 타입을 표기한다. 그러면 타입보다 덜 증명하는 검증기가 컴파일 오류가 된다. 아래에서 `name`을 지우면 대입이 실패한다.

```ts
type User = { id: string; name: string };

const userSchema: z.ZodType<User> = z.object({ id: z.string(), name: z.string() });
```

기존 `as`를 없앨 때는 추론 실패 원인에 따라 처리한다.

| 추론 실패 원인 | 처리 |
|---|---|
| 판별자 없음 | 판별자를 더해 판별 유니온으로 바꾼다 |
| 지나치게 넓은 원본 타입(예: `Record<string, unknown>`) | 좁힌다 |
| 타입 없는 경계 | 그 모양을 소유한 스키마로 파싱한다. 스키마는 없는 곳에만 더한다 |
| 정말 표현할 수 없음 | 브랜드 타입이나 `satisfies`를 쓴다 |

## 좁히기 위계

가장 좋은 것부터 최후 수단까지 다음 순서로 쓴다.

1. 판별 유니온의 switch나 if. 컴파일러가 자동으로 좁힌다.
2. `in` 연산자. `'key' in obj`는 그 키를 가진 변형으로 좁힌다.
3. `typeof`와 `instanceof`. 원시 타입과 클래스 인스턴스에 쓴다.
4. 사용자 정의 타입 가드. 위의 방법으로 모자랄 때 쓴다.
5. `as` 캐스트. 검증한 뒤에만 쓴다.

```ts
function area(s: Shape): number {
  if ('radius' in s) return Math.PI * s.radius ** 2; // narrowed to circle
  return s.width * s.height; // narrowed to rect
}
```

## 타입 가드

- 가드는 주장을 실제로 확인해야 한다. 거짓 가드는 안전해 보이는 이름 뒤에 버그를 숨기므로 `as`보다 나쁘다.
- 가능하면 판별자로 먼저 좁힌다.

```ts
function isCircle(s: Shape): s is Shape & { kind: 'circle' } {
  return s.kind === 'circle';
}
```

## 빠짐없음 검사

- default 분기에서 판별 대상을 `never` 타입 지역 변수에 대입한다.
- 값을 돌려주는 switch는 return 방식, 문장 switch는 void 방식을 쓴다.

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

```ts
// Don't. Widens, loses literal types.
const config = { theme: 'dark', cols: 3 } as Config;

// Do. Validates AND preserves literal types.
const config = { theme: 'dark', cols: 3 } satisfies Config;
// config.theme is 'dark' (literal), not string
```

## 경계 검증

- 데이터가 들어오는 곳에서 한 번 검증하고 안에서는 타입을 믿는다.
- 전송 형식(proto, JSON-RPC)은 상위 호환 변경이 옛 클라이언트를 깨지 않도록 `ignoreUnknownFields`로 파싱한다.
- 저장된 JSON은 버전 정보를 붙여 저장하고 파싱 실패를 처리한다.
- 호출 사슬 깊은 곳에서 다시 검증하지 않는다.

## 스키마에서 도출한 타입

- `.proto`, OpenAPI 명세, GraphQL 스키마, 데이터베이스 마이그레이션이 모양을 정의하면 생성된 타입에서 도출한다. 같은 모양을 다시 정의하지 않는다.

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

- 핫 패스는 예외다. 프레임마다 렌더, 토크나이저, 파서, 할당 비용이 중요한 촘촘한 루프가 여기에 든다.

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
