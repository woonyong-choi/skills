# TypeScript 패턴

`SKILL.md`의 규칙마다 둔 코드 예제다. 바탕 원칙은 언어와 상관없다. **type-system-discipline**과 **boundary-discipline** 원칙 스킬을 본다.

## 브랜드 타입

원시 타입에 브랜드를 붙여 서로 섞이지 않게 한다. 경계에서 한 번 검증한다. 하류 코드는 타입을 믿는다.

```ts
type AgentId = string & { readonly __brand: "AgentId" };

function parseAgentId(input: string): AgentId {
  if (!isUUID(input)) throw new Error(`Invalid agent id: ${input}`);
  return input as AgentId;
}

function focusAgent(id: AgentId): void {
  /* input is trusted */
}
```

`readonly __brand: 'X'` 모양을 따른다. 새 관례를 지어내지 않는다.

## 판별 유니온

변형은 리터럴 판별자로 모델링한다. 모든 변형이 같은 필드 이름을 공유하고 변형마다 값이 고유하므로 불가능한 조합을 표현할 수 없다.

```ts
// Don't. Boolean + optionals lets contradictory states exist.
type DiffState = { loading: boolean; diff?: GitDiff; error?: string };

// Do. Only valid states exist.
type DiffState =
  | { kind: "loading" }
  | { kind: "ready"; diff: GitDiff }
  | { kind: "error"; error: string };
```

판별자 이름 하나(`kind`, `type`, `tag`)를 골라 고수한다.

## 구성적 모델링

느슨한 타입을 런타임 검사로 제한하지 말고, 모두 합법인 부품으로 타입을 짠다.

비어 있지 않음, 가변 길이 튜플로:

```ts
type NonEmpty<T> = [T, ...T[]];

// Don't: T[] plus a length check every caller must repeat
function pickWinner(entries: string[]): string {
  if (entries.length === 0) throw new Error("no entries");
  return entries[Math.floor(Math.random() * entries.length)];
}

// Do: an empty value of the type can't exist
function pickWinner(entries: NonEmpty<string>): string {
  return entries[Math.floor(Math.random() * entries.length)];
}
```

평범한 `T[]`가 들어오는 곳에서는 가드로 한 번 좁힌다. 그러면 그 사실이 타입에 실려 다닌다.

```ts
const isNonEmpty = <T>(arr: T[]): arr is NonEmpty<T> => arr.length > 0;
```

짝수 길이, 쌍으로:

```ts
type Pairs<T> = [T, T][];
```

시간 범위, 시작과 길이로:

```ts
// Don't: a comment holds the invariant
type TimeRange = { start: Date; end: Date }; // start <= end

// Do: a negative range can't be written; derive end when needed
type TimeRange = { start: Date; durationMs: number };
```

`durationMs`는 평범한 숫자로 둔다. 길이를 기대하는 곳에 날 숫자가 넘어올 수 있을 때만 브랜드 타입 절에 따라 브랜드를 붙이고, 습관적으로 붙이지 않는다. 나쁜 상태를 만들 수 없게 하는 표현을 고른 뒤, 필요한 읽기 방식을 그 위에 드러낸다(`pairs.flat()`, `rangeEnd()` 헬퍼).

## 가장 단순한 전함수 타입

모든 것을 강화하지 않는다. 그 위의 모든 연산이 전함수이면 `T[]`를 유지한다.

```ts
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0); // [] is 0, fine
```

느슨한 타입이 사용 지점에서 거짓말을 강요할 때 강화한다. 신호는 `!`, `arr[0] as T`, "일어날 리 없음" throw다.

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

결과를 `Session | undefined`로 약하게 하는 것이 또 하나의 전함수 시그니처다.

## `any`보다 `unknown`

외부 데이터는 언제나 `unknown`이다. 쓰기 전에 좁힌다.

```ts
// Don't
function handle(input: any) {
  return input.foo.bar;
}

// Do
function handle(input: unknown) {
  if (typeof input === "object" && input !== null && "foo" in input) {
    // narrowed; compiler verifies access
  }
}
```

외부 출처에는 RPC 페이로드, `JSON.parse`, `postMessage`, IPC, 파일 내용, 환경 변수, 데이터베이스 결과가 있다.

## 손으로 쓴 가드보다 스키마 먼저

외부 데이터에 속성마다 확인하는 타입 가드를 쓰기 전에, 저장소의 런타임 스키마 라이브러리와 기존 스키마를 찾는다. 스키마 하나가 검증을 소유하게 하고 TypeScript 타입은 거기서 끌어낸다. 서로 어긋날 수 있는 스키마, 중복 인터페이스, 가드를 따로 유지하지 않는다.

```ts
import { z } from "zod";

const UserSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(["admin", "member"]),
});

type User = z.infer<typeof UserSchema>;

function parseUser(input: unknown): User {
  return UserSchema.parse(input);
}
```

실패가 예상되는 갈래이면 `safeParse`를 쓴다. 저장소가 다른 스키마 라이브러리를 쓰면 그 라이브러리의 같은 추론 헬퍼를 쓴다. 가드 하나를 위해 새 스키마 의존성을 더하지 않는다. 이 규칙은 코드베이스가 이미 믿는 스키마 체계를 택한다.

## `as` 캐스트 금지

모든 `as`는 잠재적 런타임 충돌이다. 타입 시스템이 주장을 확인한 뒤에만 캐스트한다.

```ts
import { z } from "zod";

// Don't
const user = data as User;

// Don't
function isUser(data: unknown): data is User {
  return typeof data === "object" && data !== null && "id" in data;
}

// Do
const userSchema = z.object({ id: z.string(), name: z.string() });
type User = z.infer<typeof userSchema>;

function parseUser(data: unknown): User {
  return userSchema.parse(data);
}
```

타입이 먼저 있을 때는 검증기에 그것이 증명하는 타입을 붙인다. 그러면 타입보다 덜 증명하는 검증기를 컴파일러가 거부한다. 아래 객체에서 `name`을 빼면 대입이 컴파일되지 않는다.

```ts
type User = { id: string; name: string };

const userSchema: z.ZodType<User> = z.object({ id: z.string(), name: z.string() });
```

기존 코드에서 `as`를 리팩터링으로 없앨 때는 TypeScript가 왜 추론하지 못하는지 찾는다.

- 판별자가 없음: 하나 더하고 판별 유니온으로 바꾼다.
- 원본 타입이 지나치게 넓음(예: `Record<string, unknown>`): 좁힌다.
- 타입 없는 경계: 그 모양을 소유한 스키마로 파싱한다. 스키마가 없는 곳에만 더한다.
- 정말 표현할 수 없음: 브랜드 타입이나 `satisfies`를 쓴다.

## 좁히기 위계

가장 좋은 것부터 최후 수단까지:

1. **판별 유니온 switch / if.** 컴파일러가 자동으로 좁힌다.
2. **`in` 연산자.** `"key" in obj`는 그 키를 가진 변형으로 좁힌다.
3. **`typeof` / `instanceof`.** 원시 타입과 클래스 인스턴스에 쓴다.
4. **사용자 정의 타입 가드.** 위의 것으로 모자랄 때 쓴다.
5. **`as` 캐스트.** 검증한 뒤에만 쓴다.

```ts
function area(s: Shape): number {
  if ("radius" in s) return Math.PI * s.radius ** 2; // narrowed to circle
  return s.width * s.height; // narrowed to rect
}
```

## 타입 가드

가드는 주장을 실제로 확인해야 한다. 거짓말하는 가드는 `as`보다 나쁘다.

```ts
function isCircle(s: Shape): s is Shape & { kind: "circle" } {
  return s.kind === "circle";
}
```

가능하면 판별자로 좁히는 쪽을 택한다.

## 빠짐없음 검사

default 갈래에서 판별 대상을 `never` 타입 지역 변수에 대입한다.

```ts
// Value-returning switch
function area(s: Shape): number {
  switch (s.kind) {
    case "circle":
      return Math.PI * s.radius ** 2;
    case "rect":
      return s.width * s.height;
    default: {
      const _exhaustive: never = s;
      return _exhaustive;
    }
  }
}

// Void switch
function handle(s: Shape): void {
  switch (s.kind) {
    case "circle":
      drawCircle(s);
      break;
    case "rect":
      drawRect(s);
      break;
    default: {
      const _exhaustive: never = s;
      void _exhaustive;
    }
  }
}
```

값을 돌려주는 switch에서는 return 방식, 문장 switch에서는 void 방식을 쓴다.

## `as`보다 `satisfies`

`satisfies`는 리터럴 타입을 넓히지 않고 검증한다.

```ts
// Don't. Widens, loses literal types.
const config = { theme: "dark", cols: 3 } as Config;

// Do. Validates AND preserves literal types.
const config = { theme: "dark", cols: 3 } satisfies Config;
// config.theme is "dark" (literal), not string
```

## 경계 검증

데이터가 들어오는 곳에서 한 번 검증한다. 안에서는 타입을 믿는다. **boundary-discipline** 원칙 스킬을 본다.

- **전송 형식**(proto, JSON-RPC): 앞으로 호환되는 변경이 옛 클라이언트를 깨지 않도록 `ignoreUnknownFields`로 파싱한다.
- **저장된 JSON:** 버전이 붙은 덩어리로 두고 파싱을 try/catch로 감싼다.
- 호출 사슬 깊은 곳에서 **다시 검증하지 않는다**.

## 스키마에서 끌어낸 타입

`.proto`, OpenAPI 명세, GraphQL 스키마, 데이터베이스 마이그레이션이 이미 모양을 정의하면 중복하지 말고 생성된 타입에서 끌어낸다.

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
import type { ChecksMessage } from "<generated module>";
function renderChecks(s: Pick<ChecksMessage, "totalCount" | "checks">) {
  /* ... */
}
```

새 인터페이스를 쓰기 전에 `Pick`, `Omit`, `Parameters`, `ReturnType`, `Awaited`, `typeof`를 먼저 쓴다.

## 객체 인자

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

뜨거운 경로에서는 건너뛴다. 프레임마다 렌더, 토크나이저, 파서, 할당 비용이 중요한 촘촘한 반복문 안의 모든 것이다.
