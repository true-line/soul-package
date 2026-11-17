import assert from 'node:assert/strict';
import test from 'node:test';
import { validateDependencies } from '../src/manifest/dependencies.mjs';

test('accepts an empty graph and a package with shared dependencies', () => {
  validateDependencies(new Map());
  validateDependencies(new Map([
    ['root', ['a', 'b']], ['a', ['leaf']], ['b', ['leaf']], ['leaf', []],
  ]));
});

test('refuses self-reference and cycles outside the first component', () => {
  assert.throws(() => validateDependencies(new Map([['a', ['a']]])), /Dependency cycle/);
  assert.throws(() => validateDependencies(new Map([
    ['leaf', []], ['a', ['b']], ['b', ['c']], ['c', ['a']],
  ])), /Dependency cycle/);
});

test('refuses incomplete graphs and malformed declarations', () => {
  assert.throws(() => validateDependencies(new Map([['a', ['absent']]])), /Unresolved dependency/);
  assert.throws(() => validateDependencies(new Map([['a', [null]]])), /Unresolved dependency/);
  assert.throws(() => validateDependencies(new Map([['a', 'leaf']])), TypeError);
  assert.throws(() => validateDependencies(new Map([[null, []]])), TypeError);
  assert.throws(() => validateDependencies({}), TypeError);
});

test('accepts a deep acyclic chain without recursion', () => {
  const graph = new Map();
  for (let i = 0; i < 20000; i++) graph.set(String(i), [String(i + 1)]);
  graph.set('20000', []);
  validateDependencies(graph);
});
