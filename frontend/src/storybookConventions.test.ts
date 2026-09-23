import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const sourceRoot = dirname(fileURLToPath(import.meta.url));

const statusTagByRoot = {
  "In Development": "status-in-development",
  Production: "status-production",
  Reference: "status-reference",
} as const;

function collectStoryFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = join(directory, entry.name);
    if (entry.isDirectory()) return collectStoryFiles(entryPath);
    return /\.stories\.tsx?$/.test(entry.name) ? [entryPath] : [];
  });
}

function collectFeatureComponents(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = join(directory, entry.name);
    if (entry.isDirectory()) return collectFeatureComponents(entryPath);
    if (!entry.name.endsWith(".tsx")) return [];
    if (/(?:\.test|\.stories|\.testSetup|TestHelpers)\.tsx$/.test(entry.name)) return [];
    return [entryPath];
  });
}

function resolveRelativeModule(filePath: string, moduleName: string): string | null {
  const basePath = resolve(dirname(filePath), moduleName);
  const candidates = [
    basePath,
    `${basePath}.ts`,
    `${basePath}.tsx`,
    join(basePath, "index.ts"),
    join(basePath, "index.tsx"),
  ];
  return (
    candidates.find((candidate) => existsSync(candidate) && statSync(candidate).isFile()) ?? null
  );
}

function storyReachableSources(storyFiles: string[]): Set<string> {
  const reachable = new Set<string>();
  const pending = [...storyFiles];

  while (pending.length > 0) {
    const filePath = pending.pop()!;
    if (reachable.has(filePath)) continue;
    reachable.add(filePath);

    const sourceFile = parseSourceFile(filePath);
    for (const statement of sourceFile.statements) {
      if (!ts.isImportDeclaration(statement) && !ts.isExportDeclaration(statement)) continue;
      const moduleSpecifier = statement.moduleSpecifier;
      if (!moduleSpecifier || !ts.isStringLiteral(moduleSpecifier)) continue;
      if (!moduleSpecifier.text.startsWith(".")) continue;
      const dependency = resolveRelativeModule(filePath, moduleSpecifier.text);
      if (dependency) pending.push(dependency);
    }
  }

  return reachable;
}

function unwrapExpression(expression: ts.Expression): ts.Expression {
  if (
    ts.isAsExpression(expression) ||
    ts.isParenthesizedExpression(expression) ||
    ts.isSatisfiesExpression(expression)
  ) {
    return unwrapExpression(expression.expression);
  }
  return expression;
}

function propertyName(property: ts.ObjectLiteralElementLike): string | undefined {
  if (!property.name) return undefined;
  if (
    ts.isIdentifier(property.name) ||
    ts.isStringLiteral(property.name) ||
    ts.isNumericLiteral(property.name)
  ) {
    return property.name.text;
  }
  return undefined;
}

function propertyValue(
  object: ts.ObjectLiteralExpression,
  name: string,
): ts.Expression | undefined {
  const property = object.properties.find(
    (candidate) => ts.isPropertyAssignment(candidate) && propertyName(candidate) === name,
  );
  return property && ts.isPropertyAssignment(property)
    ? unwrapExpression(property.initializer)
    : undefined;
}

function stringValue(expression: ts.Expression | undefined): string | undefined {
  return expression &&
    (ts.isStringLiteral(expression) || ts.isNoSubstitutionTemplateLiteral(expression))
    ? expression.text
    : undefined;
}

function defaultMeta(sourceFile: ts.SourceFile): ts.ObjectLiteralExpression | undefined {
  const exportAssignment = sourceFile.statements.find(ts.isExportAssignment);
  if (!exportAssignment) return undefined;

  const exported = unwrapExpression(exportAssignment.expression);
  if (ts.isObjectLiteralExpression(exported)) return exported;
  if (!ts.isIdentifier(exported)) return undefined;

  for (const statement of sourceFile.statements) {
    if (!ts.isVariableStatement(statement)) continue;
    for (const declaration of statement.declarationList.declarations) {
      if (!ts.isIdentifier(declaration.name) || declaration.name.text !== exported.text) continue;
      if (!declaration.initializer) return undefined;
      const initializer = unwrapExpression(declaration.initializer);
      return ts.isObjectLiteralExpression(initializer) ? initializer : undefined;
    }
  }
  return undefined;
}

function exportedStoryObjects(sourceFile: ts.SourceFile) {
  return sourceFile.statements.flatMap((statement) => {
    if (
      !ts.isVariableStatement(statement) ||
      !statement.modifiers?.some((modifier) => modifier.kind === ts.SyntaxKind.ExportKeyword)
    ) {
      return [];
    }

    return statement.declarationList.declarations.flatMap((declaration) => {
      if (!ts.isIdentifier(declaration.name) || !declaration.initializer) return [];
      const initializer = unwrapExpression(declaration.initializer);
      return ts.isObjectLiteralExpression(initializer)
        ? [{ exportName: declaration.name.text, story: initializer }]
        : [];
    });
  });
}

function displayNameFromExport(exportName: string): string {
  const words = exportName
    .replace(/_/g, " ")
    .replace(/([a-z\d])([A-Z])/g, "$1 $2")
    .replace(/([A-Z])([A-Z][a-z])/g, "$1 $2");
  return `${words.charAt(0).toUpperCase()}${words.slice(1)}`;
}

function viewportCatalogueNames(): Set<string> {
  const cataloguePath = join(sourceRoot, "storybook", "viewports.ts");
  const sourceFile = ts.createSourceFile(
    cataloguePath,
    readFileSync(cataloguePath, "utf8"),
    ts.ScriptTarget.Latest,
    true,
    ts.ScriptKind.TS,
  );
  const names = new Set<string>();
  function visit(node: ts.Node): void {
    if (ts.isVariableStatement(node)) {
      for (const declaration of node.declarationList.declarations) {
        if (
          ts.isIdentifier(declaration.name) &&
          declaration.name.text === "storybookViewports" &&
          declaration.initializer &&
          ts.isObjectLiteralExpression(unwrapExpression(declaration.initializer))
        ) {
          const options = unwrapExpression(declaration.initializer) as ts.ObjectLiteralExpression;
          for (const property of options.properties) {
            if (ts.isPropertyAssignment(property)) {
              const key = propertyName(property);
              if (key) names.add(key);
            } else if (ts.isShorthandPropertyAssignment(property)) {
              names.add(property.name.text);
            }
          }
        }
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(sourceFile);
  return names;
}

function collectViewportReferences(sourceFile: ts.SourceFile): string[] {
  const references: string[] = [];
  function visit(node: ts.Node): void {
    if (ts.isPropertyAssignment(node) && propertyName(node) === "defaultViewport") {
      const value = stringValue(unwrapExpression(node.initializer));
      if (value) references.push(value);
    }
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      node.expression.text === "storyViewport" &&
      node.arguments.length > 0
    ) {
      const value = stringValue(unwrapExpression(node.arguments[0]!));
      if (value) references.push(value);
    }
    ts.forEachChild(node, visit);
  }
  visit(sourceFile);
  return references;
}

function parseSourceFile(filePath: string): ts.SourceFile {
  return ts.createSourceFile(
    filePath,
    readFileSync(filePath, "utf8"),
    ts.ScriptTarget.Latest,
    true,
    filePath.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
}

describe("Storybook conventions", () => {
  it("discovers stories from every feature directory", () => {
    const configPath = join(sourceRoot, "..", ".storybook", "main.ts");
    expect(readFileSync(configPath, "utf8")).toContain('"../src/features/**/*.stories.@(ts|tsx)"');
  });

  it("keeps every feature component reachable from a story", () => {
    const reachable = storyReachableSources(collectStoryFiles(sourceRoot));
    const missing = collectFeatureComponents(join(sourceRoot, "features"))
      .filter((filePath) => !reachable.has(filePath))
      .map((filePath) => relative(sourceRoot, filePath).replaceAll("\\", "/"))
      .sort();

    expect(missing).toEqual([]);
  });

  it("keeps titles, status tags, and display names consistent", () => {
    const errors: string[] = [];
    const displayNamesByTitle = new Map<string, Map<string, string>>();
    const storyFiles = collectStoryFiles(sourceRoot);

    expect(storyFiles.length).toBeGreaterThan(0);

    for (const filePath of storyFiles) {
      const file = relative(sourceRoot, filePath).replaceAll("\\", "/");
      const sourceFile = ts.createSourceFile(
        filePath,
        readFileSync(filePath, "utf8"),
        ts.ScriptTarget.Latest,
        true,
        filePath.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
      );
      const meta = defaultMeta(sourceFile);
      if (!meta) {
        errors.push(`${file}: default export must resolve to a metadata object`);
        continue;
      }

      const title = stringValue(propertyValue(meta, "title"));
      if (!title) {
        errors.push(`${file}: metadata must have a literal title`);
        continue;
      }

      const root = title.split("/")[0] as keyof typeof statusTagByRoot;
      const expectedStatusTag = statusTagByRoot[root];
      if (!expectedStatusTag) {
        errors.push(`${file}: title must begin with Production, In Development, or Reference`);
      }

      const tagsExpression = propertyValue(meta, "tags");
      const tags =
        tagsExpression && ts.isArrayLiteralExpression(tagsExpression)
          ? tagsExpression.elements.flatMap((element) => {
              const value = stringValue(element);
              return value ? [value] : [];
            })
          : [];
      const statusTags = tags.filter((tag) => tag.startsWith("status-"));
      if (statusTags.length !== 1 || statusTags[0] !== expectedStatusTag) {
        errors.push(`${file}: ${title} must have exactly the tag ${expectedStatusTag}`);
      }

      const namesForTitle = displayNamesByTitle.get(title) ?? new Map<string, string>();
      displayNamesByTitle.set(title, namesForTitle);
      for (const { exportName, story } of exportedStoryObjects(sourceFile)) {
        const explicitName = stringValue(propertyValue(story, "name"));
        const displayName = explicitName ?? displayNameFromExport(exportName);
        if (explicitName?.includes(" - ")) {
          errors.push(`${file}: ${exportName} must use an em dash instead of a spaced hyphen`);
        }
        const existingStory = namesForTitle.get(displayName);
        if (existingStory) {
          errors.push(
            `${file}: ${exportName} duplicates display name "${displayName}" from ${existingStory}`,
          );
        } else {
          namesForTitle.set(displayName, `${file}:${exportName}`);
        }
      }
    }

    expect(errors).toEqual([]);
  });

  it("uses only shared catalogue viewport presets", () => {
    const catalogue = viewportCatalogueNames();
    expect(catalogue.size).toBeGreaterThan(0);

    const errors: string[] = [];
    for (const filePath of collectStoryFiles(sourceRoot)) {
      const file = relative(sourceRoot, filePath).replaceAll("\\", "/");
      const references = collectViewportReferences(parseSourceFile(filePath));
      for (const name of references) {
        if (!catalogue.has(name)) {
          errors.push(`${file}: viewport preset "${name}" is not in the shared catalogue`);
        }
      }
    }

    expect(errors).toEqual([]);
  });
});
