const express = require('express');
const Solver = require('./solver');
const app = express();

app.use(express.json());

app.post('/solve', async (req, res) => {
    const { url, sitekey, invisible } = req.body;
    if (!url || !sitekey) return res.status(400).json({ error: 'Missing url or sitekey' });
    const solver = new Solver();
    const token = await solver.solve(url, sitekey, invisible || false);
    res.json({ token });
});

app.get('/', (req, res) => res.send('Turnstile Solver is running.'));

app.listen(process.env.PORT || 10000, () => console.log('Server started'));