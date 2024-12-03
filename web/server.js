const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const axios = require('axios');
const path = require('path');
const fs = require('fs');
const puppeteer = require('puppeteer');
const { exec } = require('child_process');
const cheerio = require('cheerio');

const app = express();
const port = 3000;

// Rate limiting configuration
const rateLimitWindowMs = 60 * 60 * 1000; // 1 hour window
const maxRequestsPerWindow = 50; // Maximum requests per window
const requestTimestamps = [];

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// Ollama API configuration
const OLLAMA_API = 'http://localhost:11434';
const DEFAULT_MODEL = process.env.OLLAMA_MODEL || 'mistral';

// Load system prompt
const SYSTEM_PROMPT = fs.readFileSync(path.join(__dirname, '..', 'prompt.txt'), 'utf8');

// Rate limit check function
function checkRateLimit() {
    const now = Date.now();
    // Remove timestamps older than the window
    while (requestTimestamps.length > 0 && now - requestTimestamps[0] >= rateLimitWindowMs) {
        requestTimestamps.shift();
    }

    if (requestTimestamps.length >= maxRequestsPerWindow) {
        const oldestTimestamp = requestTimestamps[0];
        const resetTime = new Date(oldestTimestamp + rateLimitWindowMs);
        const minutesToWait = Math.ceil((resetTime - now) / (60 * 1000));
        const resetTimeStr = resetTime.toLocaleTimeString('en-US', {
            hour: 'numeric',
            minute: 'numeric',
            hour12: true
        });
        throw new Error(`Rate limit exceeded. Please try again at ${resetTimeStr} (in ${minutesToWait} minutes).`);
    }

    requestTimestamps.push(now);
}

// Search engines configuration
const searchEngines = {
    google: {
        url: 'https://www.google.com/search?q=',
        resultSelector: 'div.g',
        titleSelector: 'h3',
        linkSelector: 'a',
        snippetSelector: 'div.VwiC3b'
    },
    bing: {
        url: 'https://www.bing.com/search?q=',
        resultSelector: 'li.b_algo',
        titleSelector: 'h2',
        linkSelector: 'a',
        snippetSelector: 'div.b_caption p'
    },
    duckduckgo: {
        url: 'https://duckduckgo.com/html/?q=',
        resultSelector: 'div.result',
        titleSelector: 'h2',
        linkSelector: 'a.result__a',
        snippetSelector: 'div.result__snippet'
    }
};

// Search result ranking function
function rankResults(results) {
    return results.sort((a, b) => {
        // Simple ranking based on title and snippet relevance
        const scoreA = (a.title.length + a.snippet.length) / 2;
        const scoreB = (b.title.length + b.snippet.length) / 2;
        return scoreB - scoreA;
    });
}

// Search function for a single engine
async function searchEngine(browser, engine, query) {
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');

    try {
        await page.goto(engine.url + encodeURIComponent(query), { waitUntil: 'networkidle0' });
        const content = await page.content();
        const $ = cheerio.load(content);

        const results = [];
        $(engine.resultSelector).each((i, elem) => {
            if (i < 5) { // Get top 5 results from each engine
                const title = $(elem).find(engine.titleSelector).text().trim();
                const link = $(elem).find(engine.linkSelector).attr('href');
                const snippet = $(elem).find(engine.snippetSelector).text().trim();

                if (title && link && snippet) {
                    results.push({ title, link, snippet, engine: engine.name });
                }
            }
        });

        return results;
    } catch (error) {
        console.error(`Error searching ${engine.name}:`, error);
        return [];
    } finally {
        await page.close();
    }
}

// Function to open URL in Chrome
function openInChrome(url) {
    return new Promise((resolve, reject) => {
        exec(`start chrome "${url}"`, (error) => {
            if (error) {
                console.error('Error opening Chrome:', error);
                reject(error);
            } else {
                resolve();
            }
        });
    });
}

// Brainstorm prompts for different categories
const brainstormPrompts = {
    project: {
        system: `You are a creative project advisor. Generate 3 unique and innovative project ideas.
For each idea include:
- Title: A catchy, descriptive title
- Description: A brief overview of the project
- Key Features: 3 main features or components
- Difficulty: Easy/Medium/Hard
- Time Estimate: Approximate time to complete`,
        userFormat: `Generate 3 innovative project ideas related to: "{topic}"`
    },
    writing: {
        system: `You are a creative writing prompt generator. Generate 3 unique and engaging writing prompts.
For each prompt include:
- Title: An intriguing title
- Genre: The suggested genre
- Premise: The main story concept
- Key Elements: 3 elements to include
- Word Count: Suggested length`,
        userFormat: `Generate 3 creative writing prompts about: "{topic}"`
    },
    assignment: {
        system: `You are an educational assignment designer. Generate 3 unique and engaging assignment ideas.
For each assignment include:
- Title: A clear, educational title
- Learning Objectives: Key learning goals
- Description: What students will do
- Deliverables: What students should submit
- Duration: Estimated time to complete`,
        userFormat: `Generate 3 educational assignment ideas for: "{topic}"`
    },
    general: {
        system: `You are a creative idea generator. Generate 3 unique and practical ideas.
For each idea include:
- Title: A descriptive title
- Overview: Main concept
- Benefits: Key advantages
- Implementation: How to execute
- Resources: What's needed`,
        userFormat: `Generate 3 creative ideas about: "{topic}"`
    }
};

// Dictionary API configuration
const DICTIONARY_APIS = {
    merriamWebster: {
        url: 'https://www.merriam-webster.com/dictionary/',
        selectors: {
            pronunciation: '.prs',
            phonetics: '.pr',
            meanings: '.dtText',
            partOfSpeech: '.fl',
            etymology: '.et'
        }
    },
    dictionary: {
        url: 'https://www.dictionary.com/browse/',
        selectors: {
            pronunciation: '.pron-spell-content',
            meanings: '.one-click-content .css-nnyc96',
            partOfSpeech: '.pos',
            etymology: '.etymology'
        }
    }
};

// Fetch definition from a dictionary source
async function fetchDefinition(word, source) {
    try {
        const response = await axios.get(source.url + encodeURIComponent(word), {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        });

        const $ = cheerio.load(response.data);
        const definition = {
            source: source.url,
            pronunciation: $(source.selectors.pronunciation).first().text().trim(),
            phonetics: $(source.selectors.phonetics).first().text().trim(),
            meanings: [],
            etymology: $(source.selectors.etymology).first().text().trim()
        };

        // Get all meanings with their parts of speech
        $(source.selectors.meanings).each((i, elem) => {
            const meaning = $(elem).text().trim();
            const partOfSpeech = $(elem).closest('section').find(source.selectors.partOfSpeech).first().text().trim();
            if (meaning && !meaning.includes('Advertisement')) {
                definition.meanings.push({ partOfSpeech, meaning });
            }
        });

        return definition;
    } catch (error) {
        console.error(`Error fetching from ${source.url}:`, error);
        return null;
    }
}

// Command handlers
const commandHandlers = {
    help: async (res) => {
        const helpText = `Available commands:
- help: Show this help message
- define <word>: Get the definition of a word
- search <query>: Search for information
- summarize <text>: Summarize a piece of text
- compare <thing1> vs <thing2>: Compare two things
- brainstorm <topic> [--type <type>]: Generate ideas about a topic`;

        res.write(`data: ${JSON.stringify({ text: helpText })}\n\n`);
        res.write('data: [DONE]\n\n');
        res.end();
    },

    define: async (term, res) => {
        if (!term) {
            throw new Error('Please provide a word to define');
        }

        res.write(`data: ${JSON.stringify({ text: `📚 Looking up definitions for "${term}"...\n\n` })}\n\n`);

        try {
            // Fetch definitions from multiple sources
            const definitionPromises = Object.values(DICTIONARY_APIS).map(source =>
                fetchDefinition(term, source)
            );

            const definitions = (await Promise.all(definitionPromises)).filter(def => def !== null);

            if (definitions.length === 0) {
                res.write(`data: ${JSON.stringify({ text: `Could not find definitions for "${term}". Please check the spelling and try again.\n` })}\n\n`);
                res.write('data: [DONE]\n\n');
                return;
            }

            // Format the response
            let response = `📖 Definitions for "${term}"\n\n`;

            // Add pronunciation and phonetics if available
            const pronunciation = definitions.find(d => d.pronunciation)?.pronunciation;
            const phonetics = definitions.find(d => d.phonetics)?.phonetics;
            if (pronunciation || phonetics) {
                response += `🗣️ Pronunciation: ${pronunciation || phonetics || 'Not available'}\n\n`;
            }

            // Add meanings grouped by part of speech
            response += `📝 Meanings:\n\n`;
            const allMeanings = definitions.flatMap(d => d.meanings);
            const groupedMeanings = allMeanings.reduce((acc, { partOfSpeech, meaning }) => {
                if (!acc[partOfSpeech]) acc[partOfSpeech] = [];
                if (!acc[partOfSpeech].includes(meaning)) {
                    acc[partOfSpeech].push(meaning);
                }
                return acc;
            }, {});

            Object.entries(groupedMeanings).forEach(([pos, meanings]) => {
                response += `${pos}:\n`;
                meanings.forEach((meaning, i) => {
                    response += `${i + 1}. ${meaning}\n`;
                });
                response += '\n';
            });

            // Add etymology if available
            const etymology = definitions.find(d => d.etymology)?.etymology;
            if (etymology) {
                response += `📜 Etymology:\n${etymology}\n\n`;
            }

            // Add sources
            response += `🔍 Sources:\n`;
            definitions.forEach(def => {
                response += `- ${def.source}\n`;
            });

            res.write(`data: ${JSON.stringify({ text: response })}\n\n`);
            res.write('data: [DONE]\n\n');
        } catch (error) {
            console.error('Definition error:', error);
            res.write(`data: ${JSON.stringify({ text: `Error looking up definition: ${error.message}\n` })}\n\n`);
            res.write('data: [DONE]\n\n');
        }
    },

    search: async (query, res) => {
        if (!query) {
            throw new Error('Please provide a search query');
        }

        res.write(`data: ${JSON.stringify({ text: `🔍 Searching across multiple engines for: "${query}"\n` })}\n\n`);

        try {
            const browser = await puppeteer.launch({ headless: "new" });
            const searchPromises = Object.entries(searchEngines).map(([name, engine]) =>
                searchEngine(browser, { ...engine, name }, query)
            );

            const results = await Promise.all(searchPromises);
            const allResults = results.flat();
            const rankedResults = rankResults(allResults);

            if (rankedResults.length === 0) {
                res.write(`data: ${JSON.stringify({ text: "No results found.\n" })}\n\n`);
                res.write('data: [DONE]\n\n');
                return;
            }

            // Open best result in Chrome
            const bestResult = rankedResults[0];
            await openInChrome(bestResult.link);

            // Format and send results
            let response = `Found ${rankedResults.length} results. Opening best match in Chrome:\n\n`;
            response += `🏆 Best Result:\n`;
            response += `Title: ${bestResult.title}\n`;
            response += `Link: ${bestResult.link}\n`;
            response += `Source: ${bestResult.engine}\n`;
            response += `Summary: ${bestResult.snippet}\n\n`;

            if (rankedResults.length > 1) {
                response += `📑 Other top results:\n`;
                rankedResults.slice(1, 4).forEach((result, index) => {
                    response += `\n${index + 2}. ${result.title}\n`;
                    response += `   Link: ${result.link}\n`;
                    response += `   Source: ${result.engine}\n`;
                });
            }

            res.write(`data: ${JSON.stringify({ text: response })}\n\n`);
            res.write('data: [DONE]\n\n');

            await browser.close();
        } catch (error) {
            console.error('Search error:', error);
            res.write(`data: ${JSON.stringify({ text: `Error performing search: ${error.message}\n` })}\n\n`);
            res.write('data: [DONE]\n\n');
        }
    },

    summarize: async (text, res) => {
        if (!text) {
            throw new Error('Please provide text to summarize');
        }
        const prompt = `Summarize this text concisely:\n${text}`;
        await streamOllamaResponse(prompt, res);
    },

    compare: async (args, res) => {
        const [thing1, thing2] = args.split(' vs ');
        if (!thing1 || !thing2) {
            throw new Error('Please use the format: compare thing1 vs thing2');
        }
        const prompt = `Compare ${thing1} and ${thing2}. List key differences:`;
        await streamOllamaResponse(prompt, res);
    },

    brainstorm: async (args, res) => {
        // Parse arguments (topic and type)
        let topic = args;
        let type = 'general';

        // Check for --type flag
        const typeMatch = args.match(/--type\s+(\w+)/);
        if (typeMatch) {
            type = typeMatch[1].toLowerCase();
            topic = args.replace(/--type\s+\w+/, '').trim();
        }

        if (!topic) {
            throw new Error('Please provide a topic to brainstorm about');
        }

        if (!brainstormPrompts[type]) {
            throw new Error(`Invalid type. Available types: ${Object.keys(brainstormPrompts).join(', ')}`);
        }

        const prompt = brainstormPrompts[type];
        const systemPrompt = prompt.system;
        const userPrompt = prompt.userFormat.replace('{topic}', topic);

        try {
            res.write(`data: ${JSON.stringify({ text: `🎨 Brainstorming ${type} ideas about: "${topic}"\n\n` })}\n\n`);

            // Get ideas from Ollama with the specific system prompt
            const response = await axios.post(`${OLLAMA_API}/api/generate`, {
                model: DEFAULT_MODEL,
                prompt: userPrompt,
                system: systemPrompt,
                stream: true
            }, {
                responseType: 'stream'
            });

            response.data.on('data', chunk => {
                try {
                    const lines = chunk.toString().split('\n').filter(line => line.trim());
                    for (const line of lines) {
                        const data = JSON.parse(line);
                        if (data.response) {
                            res.write(`data: ${JSON.stringify({ text: data.response })}\n\n`);
                        }
                        if (data.done) {
                            res.write('data: [DONE]\n\n');
                        }
                    }
                } catch (error) {
                    console.error('Error processing chunk:', error);
                }
            });

            response.data.on('end', () => {
                res.end();
            });

            response.data.on('error', error => {
                console.error('Stream error:', error);
                res.write(`data: ${JSON.stringify({ text: 'Error generating ideas' })}\n\n`);
                res.end();
            });

        } catch (error) {
            console.error('Brainstorm error:', error);
            res.write(`data: ${JSON.stringify({ text: `Error brainstorming ideas: ${error.message}\n` })}\n\n`);
            res.write('data: [DONE]\n\n');
        }
    }
};

// Stream Ollama response
async function streamOllamaResponse(prompt, res) {
    try {
        checkRateLimit();

        const response = await axios.post(`${OLLAMA_API}/api/generate`, {
            model: DEFAULT_MODEL,
            prompt: prompt,
            system: SYSTEM_PROMPT,
            stream: true
        }, {
            responseType: 'stream'
        });

        // Set up SSE headers
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');

        response.data.on('data', chunk => {
            try {
                const lines = chunk.toString().split('\n').filter(line => line.trim());
                for (const line of lines) {
                    const data = JSON.parse(line);
                    if (data.response) {
                        res.write(`data: ${JSON.stringify({ text: data.response })}\n\n`);
                    }
                    if (data.done) {
                        res.write('data: [DONE]\n\n');
                    }
                }
            } catch (error) {
                console.error('Error processing chunk:', error);
            }
        });

        response.data.on('end', () => {
            res.end();
        });

        response.data.on('error', error => {
            console.error('Stream error:', error);
            res.write(`data: ${JSON.stringify({ error: 'Stream processing error' })}\n\n`);
            res.end();
        });
    } catch (error) {
        console.error('Ollama request error:', error);
        throw error;
    }
}

// Handle chat and commands
app.post('/api/chat', async (req, res) => {
    const message = req.body.message;

    if (!message) {
        return res.status(400).json({ error: 'Message is required' });
    }

    try {
        // Parse command and arguments
        const [command, ...args] = message.trim().split(' ');
        const commandName = command.toLowerCase();
        const commandArgs = args.join(' ');

        // Check if it's a command
        if (commandHandlers[commandName]) {
            try {
                await commandHandlers[commandName](commandArgs, res);
            } catch (error) {
                console.error(`Command error (${commandName}):`, error);
                if (error.message.includes('Rate limit exceeded')) {
                    res.status(429).json({ error: error.message });
                } else {
                    res.status(400).json({ error: error.message });
                }
            }
        } else {
            // Handle as regular chat
            await streamOllamaResponse(message, res);
        }
    } catch (error) {
        console.error('Chat error:', error);
        let errorMessage = 'Failed to process message';

        if (error.response) {
            if (error.response.status === 404) {
                errorMessage = `Model '${DEFAULT_MODEL}' not found. Please ensure it's installed: ollama pull ${DEFAULT_MODEL}`;
            } else if (error.response.data?.error) {
                errorMessage = `Ollama server error: ${error.response.data.error}`;
            }
        } else if (error.code === 'ECONNREFUSED') {
            errorMessage = 'Could not connect to Ollama. Please ensure Ollama is running (ollama serve)';
        } else if (error.message) {
            errorMessage = error.message;
        }

        res.status(500).json({ error: errorMessage });
    }
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
