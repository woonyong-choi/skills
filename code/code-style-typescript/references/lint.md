# 린트 설정

ESLint와 Prettier 설정의 기준 값과 실제 저장소에 맞게 바꿀 자리를 적는다.

`eslint.config.js`:

```js
import js from '@eslint/js';
import globals from 'globals';
import sonarjs from 'eslint-plugin-sonarjs';

const defaultExportConfigs = ['eslint.config.js'];

export default [
  js.configs.recommended,
  {
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
    plugins: { sonarjs },
    rules: {
      'max-lines': ['warn', { max: 750, skipBlankLines: true, skipComments: true }],
      'max-lines-per-function': ['warn', { max: 100, skipBlankLines: true, skipComments: true }],
      'max-params': ['warn', 7],
      'max-depth': ['warn', 3],
      'sonarjs/cognitive-complexity': ['warn', 15],
      'no-throw-literal': 'error',
      'prefer-promise-reject-errors': 'error',
      'no-console': 'error',
      yoda: 'error',
      eqeqeq: 'error',
      'no-negated-condition': 'warn',
      'no-nested-ternary': 'warn',
      'prefer-const': 'error',
      'no-var': 'error',
      'no-restricted-syntax': ['error', 'ExportDefaultDeclaration'],
    },
  },
  { files: ['src/cli/**'], rules: { 'no-console': ['error', { allow: ['log', 'error'] }] } },
  { files: ['src/browser/**'], rules: { 'no-console': ['error', { allow: ['warn', 'error'] }] } },
  { files: ['test/**'], rules: { 'max-lines-per-function': 'off' } },
  { files: defaultExportConfigs, rules: { 'no-restricted-syntax': 'off' } },
];
```

- `defaultExportConfigs`에는 도구가 default export를 요구한다고 확인한 실제 설정 파일 경로를 모두 적는다.
- CLI와 브라우저 override 경로는 실제 진입점과 브라우저 코드 경로로 바꾼다. 라이브러리는 console 금지를 유지한다.
- 생성물은 확인한 실제 생성 파일 경로로만 뺀다. 이름 패턴으로 추정하지 않는다.

`.prettierrc.json` 예다. 폭은 저장소의 포매터 설정을 쓴다.

```json
{ "singleQuote": true }
```
