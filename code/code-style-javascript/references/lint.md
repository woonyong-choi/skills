# 린트 설정

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

- `defaultExportConfigs`: 도구가 default export를 요구하는 것으로 확인한 실제 설정 파일 경로를 모두 기입
- CLI·브라우저 override 경로는 실제 진입점과 브라우저 코드 경로로 교체. 라이브러리는 console 금지 유지
- 생성물 제외는 생성물 표시 또는 확인한 실제 생성 경로로 설정, 파일 이름 패턴만으로 제외 금지

`.prettierrc.json` 예. 폭은 저장소의 포매터 설정 사용:

```json
{ "singleQuote": true }
```
