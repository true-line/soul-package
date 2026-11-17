// The importer resolves declarations to package IDs before this check. The
// graph includes every package in the import, including leaves and any
// disconnected components. Checking it never loads a package or runs a plugin.
export function validateDependencies(graph) {
  if (!(graph instanceof Map)) throw new TypeError('Expected a Map of package dependencies');
  for (const [id, dependencies] of graph) {
    if (typeof id !== 'string' || id.length === 0 || !Array.isArray(dependencies)) {
      throw new TypeError('Expected a package ID and an array of dependency IDs');
    }
  }

  const completed = new Set();
  const visiting = new Set();
  for (const id of graph.keys()) {
    if (completed.has(id)) continue;

    // Use explicit frames so a deep, valid chain cannot overflow the JS stack.
    visiting.add(id);
    const stack = [{ id, edges: graph.get(id).values() }];
    while (stack.length > 0) {
      const current = stack.at(-1);
      const edge = current.edges.next();
      if (edge.done) {
        completed.add(current.id);
        visiting.delete(current.id);
        stack.pop();
        continue;
      }

      const dependency = edge.value;
      if (typeof dependency !== 'string' || !graph.has(dependency)) {
        throw new Error(`Unresolved dependency of ${current.id}`);
      }
      if (visiting.has(dependency)) {
        throw new Error(`Dependency cycle from ${current.id} to ${dependency}`);
      }
      if (!completed.has(dependency)) {
        visiting.add(dependency);
        stack.push({ id: dependency, edges: graph.get(dependency).values() });
      }
    }
  }
}
