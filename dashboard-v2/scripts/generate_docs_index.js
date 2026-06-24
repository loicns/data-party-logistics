import fs from 'fs/promises';
import path from 'path';

async function generateIndex() {
  const docsDir = path.join(process.cwd(), 'public', 'docs');
  const outFile = path.join(process.cwd(), 'public', 'docs-index.json');

  try {
    const files = await fs.readdir(docsDir);
    const docs = [];

    for (const file of files) {
      if (file.endsWith('.md')) {
        const id = file.replace('.md', '');

        // Try to read the first heading to use as a title
        const content = await fs.readFile(path.join(docsDir, file), 'utf-8');
        const match = content.match(/^#\s+(.*)/m);
        let title = match ? match[1].trim() : id.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

        docs.push({ id, title, path: `/docs/${file}` });
      }
    }

    // Sort docs alphabetically
    docs.sort((a, b) => a.id.localeCompare(b.id));

    await fs.writeFile(outFile, JSON.stringify(docs, null, 2));
    console.log(`Generated docs index with ${docs.length} documents.`);
  } catch (error) {
    console.error('Failed to generate docs index:', error);
    process.exit(1);
  }
}

generateIndex();
