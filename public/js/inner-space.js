document.addEventListener('DOMContentLoaded', function() {
    // D3.js visualiseerimise seadistamine
    const width = document.getElementById('inner-space-visualization').offsetWidth;
    const height = document.getElementById('inner-space-visualization').offsetHeight;
    
    // SVG ja <g> wrapper
    const svg = d3.select('#inner-space-visualization')
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    const g = svg.append('g');

    // Zoom funktsionaalsus
    const zoom = d3.zoom()
        .scaleExtent([0.5, 5])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });

    // SVG loomine
    svg.call(zoom);

    // Taustatähtede loomine
    function createStars() {
        const stars = [];
        for (let i = 0; i < 200; i++) {
            stars.push({
                x: Math.random() * width,
                y: Math.random() * height,
                r: Math.random() * 1.5,
                opacity: Math.random()
            });
        }
        return stars;
    }

    // Taustatähtede joonistamine
    const stars = createStars();
    g.selectAll('circle.star')
        .data(stars)
        .enter()
        .append('circle')
        .attr('class', 'star')
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('r', d => d.r)
        .style('fill', 'white')
        .style('opacity', d => d.opacity);

    // Kontrollnupud
    document.getElementById('zoom-in').addEventListener('click', () => {
        zoom.scaleBy(svg.transition().duration(300), 1.3);
    });

    document.getElementById('zoom-out').addEventListener('click', () => {
        zoom.scaleBy(svg.transition().duration(300), 0.7);
    });

    document.getElementById('reset-view').addEventListener('click', () => {
        svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
    });

    // Lugude andmete laadimine ja visualiseerimine
    function loadStories() {
        fetch('/api/stories')
            .then(response => response.json())
            .then(data => {
                visualizeStories(data);
            })
            .catch(error => console.error('Error loading stories:', error));
    }

    // Lugude visualiseerimine
    function visualizeStories(stories) {
        // Eemalda olemasolevad lood
        g.selectAll('.story-node').remove();
        g.selectAll('.connection-line').remove();

        // Loo lugude sõlmed
        const nodes = stories.map((story, i) => ({
            ...story,
            x: Math.random() * (width - 100) + 50,
            y: Math.random() * (height - 100) + 50,
            r: 20 + (story.emotional_intensity || 0) * 10,
            idx: i
        }));

        // Joonista seosed
        const connections = [];
        nodes.forEach((node, i) => {
            nodes.slice(i + 1).forEach(otherNode => {
                if (Math.random() < 0.3) { // 30% tõenäosus seose loomiseks
                    connections.push({
                        source: node,
                        target: otherNode,
                        strength: Math.random()
                    });
                }
            });
        });

        // Joonista seosed
        g.selectAll('.connection-line')
            .data(connections)
            .enter()
            .append('line')
            .attr('class', 'connection-line')
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y)
            .style('stroke', 'rgba(255, 255, 255, 0.2)')
            .style('stroke-width', d => d.strength * 2);

        // Joonista lugude sõlmed
        const storyNodes = g.selectAll('.story-node')
            .data(nodes)
            .enter()
            .append('g')
            .attr('class', 'story-node')
            .attr('transform', d => `translate(${d.x},${d.y})`);

        // Lisa ringid
        storyNodes.append('circle')
            .attr('r', d => d.r)
            .style('fill', d => `hsl(${d.idx * 137.5 % 360}, 70%, 50%)`)
            .style('opacity', 0.8);

        // Lisa tekst
        storyNodes.append('text')
            .text(d => {
                if (d.title && typeof d.title === 'string' && d.title.trim() !== '') return d.title;
                if (d.content && typeof d.content === 'string' && d.content.trim() !== '') return d.content.slice(0, 20) + '...';
                if (d.id) return `Story ${d.id}`;
                console.warn('Story node missing title/content/id:', d);
                return 'Untitled';
            })
            .attr('text-anchor', 'middle')
            .attr('dy', 4)
            .style('fill', 'white')
            .style('font-size', '12px');

        // Lisa interaktiivsus
        storyNodes.on('click', (event, d) => {
            if (!d.id) {
                alert('This story node is missing an ID and cannot show insights/connections.');
                return;
            }
            showInsights(d.id);
            showConnections(d.id);
        });

        // Lisa liikumine
        const simulation = d3.forceSimulation(nodes)
            .force('charge', d3.forceManyBody().strength(-100))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(d => d.r + 10))
            .on('tick', () => {
                storyNodes.attr('transform', d => `translate(${d.x},${d.y})`);
                g.selectAll('.connection-line')
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
            });
    }

    // Avastuste kuvamine
    function showInsights(storyId) {
        fetch(`/api/insights/${storyId}`)
            .then(response => response.json())
            .then(data => {
                const insightsContent = document.getElementById('insights-content');
                insightsContent.innerHTML = generateInsightsHTML(data);
            })
            .catch(error => console.error('Error loading insights:', error));
    }

    function generateInsightsHTML(insights) {
        if (!insights || (!insights.themes && !insights.emotions && !insights.connections)) {
            return '<p>No insights available.</p>';
        }
        return `
            <div class="insight-section">
                <h3>Themes</h3>
                <ul>
                    ${(insights.themes || []).map(theme => `<li>${theme}</li>`).join('')}
                </ul>
            </div>
            <div class="insight-section">
                <h3>Emotions</h3>
                <ul>
                    ${(insights.emotions || []).map(emotion => `<li>${emotion}</li>`).join('')}
                </ul>
            </div>
            <div class="insight-section">
                <h3>Connections</h3>
                <ul>
                    ${(insights.connections || []).map(connection => `<li>${connection}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    // Seoste kuvamine
    function showConnections(storyId) {
        fetch(`/api/connections/${storyId}`)
            .then(response => response.json())
            .then(data => {
                const connectionsList = document.getElementById('connections-list');
                connectionsList.innerHTML = generateConnectionsHTML(data);
            })
            .catch(error => console.error('Error loading connections:', error));
    }

    function generateConnectionsHTML(connections) {
        if (!connections || !connections.length) {
            return '<p>No connections found.</p>';
        }
        return `
            <ul>
                ${connections.map(conn => `<li>${conn.description || ''}</li>`).join('')}
            </ul>
        `;
    }

    // Andmete laadimine lehe avamisel
    loadStories();
}); 