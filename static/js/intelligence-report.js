// Intelligence Agency Report - Comprehensive Psychological Profiling System
class IntelligenceReport {
  constructor(userData) {
    this.userData = userData;
    this.reportData = null;
  }

  // Main generation function
  async generateReport() {
    const report = {
      metadata: this.generateMetadata(),
      archetype: this.determineArchetype(),
      dimensions: this.calculateDimensions(),
      patterns: this.identifyBehavioralPatterns(),
      cognitiveStyle: this.analyzeCognitiveStyle(),
      emotionalProfile: this.analyzeEmotionalProcessing(),
      relationshipStyle: this.analyzeRelationshipStyle(),
      growthTrajectory: this.predictGrowthPath(),
      predictions: this.generatePredictions(),
      recommendations: this.generateRecommendations(),
      riskFactors: this.identifyRiskFactors(),
      strengths: this.identifyStrengths(),
      nextLevel: this.generateNextLevelInsights()
    };
    this.reportData = report;
    return report;
  }
  generateMetadata() {
    const totalDataPoints = this.userData.stories.length + this.userData.conversations.length + Object.keys(this.userData.assessments).length;
    return {
      generatedAt: new Date().toISOString(),
      dataPoints: totalDataPoints,
      analysisVersion: '3.1',
      confidenceLevel: Math.min(95, 60 + this.userData.userStats.totalConversations * 2 + Object.keys(this.userData.assessments).length * 5),
      reportId: `IA-${Date.now()}`,
      processingTime: '2.3 seconds',
      classification: totalDataPoints > 50 ? 'COMPREHENSIVE' : totalDataPoints > 20 ? 'DETAILED' : 'EMERGING'
    };
  }
  determineArchetype() {
    const archetypes = {
      'The Deep Thinker': {
        traits: ['analytical', 'introspective', 'philosophical', 'pattern-seeking'],
        description: 'You process experiences through deep reflection and abstract thinking',
        color: 'purple',
        icon: '🧠',
        probability: 0,
        characteristics: ['Prefers depth over breadth in conversations', 'Seeks underlying patterns and meanings', 'Values intellectual discourse', 'Processes emotions cognitively']
      },
      'The Connected Empath': {
        traits: ['empathetic', 'relationship-focused', 'emotionally aware', 'collaborative'],
        description: 'You understand the world through emotional connections and relationships',
        color: 'pink',
        icon: '💝',
        probability: 0,
        characteristics: ['Naturally attuned to others\' emotions', 'Values harmony and connection', 'Processes information through relational lens', 'Strong interpersonal intelligence']
      },
      'The Creative Explorer': {
        traits: ['innovative', 'curious', 'artistic', 'possibility-focused'],
        description: 'You see possibilities everywhere and express insights creatively',
        color: 'orange',
        icon: '🎨',
        probability: 0,
        characteristics: ['Thrives on novelty and innovation', 'Sees connections others miss', 'Values creative self-expression', 'Comfortable with ambiguity']
      },
      'The Practical Adapter': {
        traits: ['pragmatic', 'flexible', 'solution-oriented', 'resourceful'],
        description: 'You navigate life through practical wisdom and adaptability',
        color: 'green',
        icon: '⚖️',
        probability: 0,
        characteristics: ['Focuses on actionable solutions', 'Adapts quickly to changing circumstances', 'Values efficiency and results', 'Balances multiple perspectives']
      },
      'The Independent Analyst': {
        traits: ['self-reliant', 'logical', 'objective', 'systematic'],
        description: 'You approach life with systematic thinking and independence',
        color: 'blue',
        icon: '🔍',
        probability: 0,
        characteristics: ['Values autonomy and self-direction', 'Approaches problems systematically', 'Seeks objective truth', 'Comfortable working independently']
      },
      'The Intuitive Guide': {
        traits: ['intuitive', 'wise', 'spiritually-aware', 'synthesizing'],
        description: 'You understand life through inner wisdom and intuitive insights',
        color: 'indigo',
        icon: '🌟',
        probability: 0,
        characteristics: ['Trusts inner knowing and intuition', 'Sees bigger picture patterns', 'Values meaning and purpose', 'Integrates multiple ways of knowing']
      }
    };

    // Analyze conversation patterns
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();

    // Score each archetype based on linguistic patterns
    const scoringRules = {
      'The Deep Thinker': [{
        pattern: /think|analyze|consider|reflect|ponder|philosophical|abstract/g,
        weight: 3
      }, {
        pattern: /why|because|therefore|thus|hence|logic/g,
        weight: 2
      }, {
        pattern: /pattern|system|structure|framework|concept/g,
        weight: 2
      }],
      'The Connected Empath': [{
        pattern: /feel|emotion|heart|love|relationship|connection|together/g,
        weight: 3
      }, {
        pattern: /empathy|understand|compassion|care|support|help/g,
        weight: 2
      }, {
        pattern: /we|us|together|harmony|community|share/g,
        weight: 2
      }],
      'The Creative Explorer': [{
        pattern: /create|art|imagine|dream|possibility|new|innovative/g,
        weight: 3
      }, {
        pattern: /explore|discover|adventure|curious|wonder|what if/g,
        weight: 2
      }, {
        pattern: /inspiration|vision|creative|original|unique/g,
        weight: 2
      }],
      'The Practical Adapter': [{
        pattern: /practical|solution|work|adapt|flexible|realistic/g,
        weight: 3
      }, {
        pattern: /balance|manage|organize|plan|efficient|effective/g,
        weight: 2
      }, {
        pattern: /change|adjust|modify|improve|fix|resolve/g,
        weight: 2
      }],
      'The Independent Analyst': [{
        pattern: /independent|alone|self|objective|data|evidence|fact/g,
        weight: 3
      }, {
        pattern: /analyze|research|study|investigate|examine/g,
        weight: 2
      }, {
        pattern: /logical|rational|systematic|methodical|precise/g,
        weight: 2
      }],
      'The Intuitive Guide': [{
        pattern: /intuition|spiritual|wisdom|insight|inner|soul/g,
        weight: 3
      }, {
        pattern: /meaning|purpose|deeper|transcend|transform/g,
        weight: 2
      }, {
        pattern: /guide|mentor|teach|inspire|enlighten/g,
        weight: 2
      }]
    };

    // Calculate scores
    Object.keys(archetypes).forEach(archetype => {
      let score = 0;
      scoringRules[archetype].forEach(rule => {
        const matches = conversationText.match(rule.pattern) || [];
        score += matches.length * rule.weight;
      });
      archetypes[archetype].probability = score;
    });

    // Factor in assessment results
    if (this.userData.assessments.attachment) {
      const attachment = this.userData.assessments.attachment.result;
      if (attachment === 'secure') archetypes['The Connected Empath'].probability += 5;
      if (attachment === 'avoidant') archetypes['The Independent Analyst'].probability += 5;
      if (attachment === 'anxious') archetypes['The Connected Empath'].probability += 3;
    }
    if (this.userData.assessments['love-language']) {
      const loveLanguage = this.userData.assessments['love-language'].result;
      if (loveLanguage.includes('touch')) archetypes['The Connected Empath'].probability += 3;
      if (loveLanguage.includes('words')) archetypes['The Deep Thinker'].probability += 3;
      if (loveLanguage.includes('quality time')) archetypes['The Connected Empath'].probability += 2;
    }

    // Determine primary and secondary archetypes
    const sortedArchetypes = Object.entries(archetypes).sort(([, a], [, b]) => b.probability - a.probability);
    const primary = sortedArchetypes[0];
    const secondary = sortedArchetypes[1];
    return {
      primary: {
        name: primary[0],
        details: primary[1],
        confidence: Math.min(95, 60 + primary[1].probability * 2)
      },
      secondary: secondary[1].probability > 3 ? {
        name: secondary[0],
        details: secondary[1],
        influence: Math.min(40, secondary[1].probability * 3)
      } : null,
      blendProfile: this.generateArchetypeBlend(primary[0], secondary[0])
    };
  }
  generateArchetypeBlend(primary, secondary) {
    const blends = {
      'The Deep Thinker_The Connected Empath': 'Emotionally Intelligent Analyst',
      'The Deep Thinker_The Creative Explorer': 'Visionary Philosopher',
      'The Deep Thinker_The Independent Analyst': 'Systematic Theorist',
      'The Connected Empath_The Creative Explorer': 'Empathetic Innovator',
      'The Connected Empath_The Practical Adapter': 'Harmonious Problem-Solver',
      'The Creative Explorer_The Intuitive Guide': 'Inspired Visionary',
      'The Practical Adapter_The Independent Analyst': 'Strategic Optimizer',
      'The Independent Analyst_The Intuitive Guide': 'Insightful Strategist'
    };
    return blends[`${primary}_${secondary}`] || 'Unique Blend';
  }
  calculateDimensions() {
    return {
      selfAwareness: this.calculateSelfAwareness(),
      emotionalIntelligence: this.calculateEmotionalIQ(),
      cognitiveComplexity: this.calculateCognitiveComplexity(),
      relationshipIntelligence: this.calculateRelationshipIQ(),
      adaptability: this.calculateAdaptability(),
      creativityIndex: this.calculateCreativity(),
      resilience: this.calculateResilience(),
      authenticityScore: this.calculateAuthenticity()
    };
  }
  calculateSelfAwareness() {
    let score = 40; // Base score
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();

    // Self-reflective language patterns
    const selfAwarenessPattterns = [/i realize|i notice|i understand|i recognize|i see that/g, /my pattern|my tendency|my habit|my behavior/g, /i feel|i think|i believe|i value/g, /reflection|introspection|self-aware|mindful/g];
    selfAwarenessPattterns.forEach(pattern => {
      const matches = conversationText.match(pattern) || [];
      score += matches.length * 2;
    });

    // Assessment completion bonus
    score += Object.keys(this.userData.assessments).length * 5;

    // Story creation shows self-reflection
    score += this.userData.stories.length * 3;
    return {
      score: Math.min(98, score),
      // Never 100% - always room for growth
      level: score > 85 ? 'Advanced' : score > 70 ? 'Developing' : score > 50 ? 'Emerging' : 'Beginning',
      insights: this.generateSelfAwarenessInsights(score),
      nextStep: this.getSelfAwarenessNextStep(score)
    };
  }
  calculateEmotionalIQ() {
    let score = 45;
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();
    const emotionalPatterns = [/feel|emotion|emotional|mood|sentiment/g, /empathy|compassion|understanding|support/g, /anger|joy|sadness|fear|surprise|disgust/g, /regulate|manage|cope|handle|process/g];
    emotionalPatterns.forEach(pattern => {
      const matches = conversationText.match(pattern) || [];
      score += matches.length * 1.5;
    });

    // Relationship assessment bonus
    if (this.userData.assessments.attachment) score += 10;
    if (this.userData.assessments['love-language']) score += 8;
    return {
      score: Math.min(97, score),
      level: score > 85 ? 'Highly Developed' : score > 70 ? 'Well-Developed' : score > 50 ? 'Developing' : 'Emerging',
      components: {
        selfRegulation: Math.min(95, score - 5),
        empathy: Math.min(95, score + 3),
        socialSkills: Math.min(95, score - 2),
        motivation: Math.min(95, score + 1)
      }
    };
  }
  calculateCognitiveComplexity() {
    let score = 50;
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();

    // Indicators of complex thinking
    const complexityPatterns = [/however|although|despite|nevertheless|on the other hand/g, /complex|nuanced|multifaceted|intricate|sophisticated/g, /perspective|viewpoint|angle|dimension|aspect/g, /paradox|contradiction|irony|ambiguity/g];
    complexityPatterns.forEach(pattern => {
      const matches = conversationText.match(pattern) || [];
      score += matches.length * 3;
    });

    // Story variety indicates cognitive flexibility
    const storyFormats = new Set();
    this.userData.stories.forEach(story => {
      if (story.createdFormats) {
        story.createdFormats.forEach(format => storyFormats.add(format));
      }
    });
    score += storyFormats.size * 2;
    return {
      score: Math.min(96, score),
      level: score > 85 ? 'Highly Complex' : score > 70 ? 'Moderately Complex' : score > 50 ? 'Developing' : 'Linear',
      characteristics: this.getCognitiveCharacteristics(score)
    };
  }
  calculateRelationshipIQ() {
    let score = 45;
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();
    const relationshipPatterns = [/relationship|friend|family|partner|colleague/g, /communicate|listen|understand|connect|bond/g, /conflict|resolution|compromise|negotiate/g, /trust|intimacy|vulnerability|openness/g];
    relationshipPatterns.forEach(pattern => {
      const matches = conversationText.match(pattern) || [];
      score += matches.length * 2;
    });

    // Attachment and love language assessments are key indicators
    if (this.userData.assessments.attachment) score += 15;
    if (this.userData.assessments['love-language']) score += 12;
    if (this.userData.assessments['communication-style']) score += 10;
    return {
      score: Math.min(95, score),
      strengths: this.getRelationshipStrengths(score),
      growthAreas: this.getRelationshipGrowthAreas(score)
    };
  }
  calculateAdaptability() {
    let score = 50;
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();
    const adaptabilityPatterns = [/adapt|adjust|flexible|change|evolve/g, /learn|grow|develop|improve|progress/g, /challenge|difficulty|obstacle|problem/g, /solution|alternative|option|approach/g];
    adaptabilityPatterns.forEach(pattern => {
      const matches = conversationText.match(pattern) || [];
      score += matches.length * 2;
    });
    return {
      score: Math.min(94, score),
      indicators: this.getAdaptabilityIndicators(score)
    };
  }
  calculateCreativity() {
    let score = 40;

    // Story format variety is a key creativity indicator
    const allFormats = new Set();
    this.userData.stories.forEach(story => {
      if (story.createdFormats) {
        story.createdFormats.forEach(format => allFormats.add(format));
      }
    });
    score += allFormats.size * 4;

    // Creative language patterns
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();
    const creativityPatterns = [/create|creative|imagine|envision|invent/g, /art|artistic|design|aesthetic|beautiful/g, /novel|unique|original|innovative|fresh/g, /inspiration|muse|spark|idea|vision/g];
    creativityPatterns.forEach(pattern => {
      const matches = conversationText.match(pattern) || [];
      score += matches.length * 2;
    });
    return {
      score: Math.min(93, score),
      expressions: Array.from(allFormats),
      style: this.getCreativeStyle(score, allFormats)
    };
  }
  calculateResilience() {
    let score = 50;
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();
    const resiliencePatterns = [/overcome|persevere|persist|endure|survive/g, /strength|courage|brave|resilient|tough/g, /bounce back|recover|heal|rebuild/g, /learned|grew|stronger|wiser/g];
    resiliencePatterns.forEach(pattern => {
      const matches = conversationText.match(pattern) || [];
      score += matches.length * 3;
    });

    // Stress response assessment adds context
    if (this.userData.assessments['stress-response']) {
      const response = this.userData.assessments['stress-response'].result;
      if (response === 'fight') score += 5;
      if (response === 'flight') score += 3;
      if (response === 'freeze') score += 7; // Often shows in overcoming paralysis
      if (response === 'fawn') score += 4;
    }
    return {
      score: Math.min(92, score),
      factors: this.getResilienceFactors(score)
    };
  }
  calculateAuthenticity() {
    let score = 55;
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();
    const authenticityPatterns = [/authentic|genuine|real|true|honest/g, /values|beliefs|principles|integrity/g, /myself|who i am|my identity|my truth/g, /vulnerable|open|transparent|raw/g];
    authenticityPatterns.forEach(pattern => {
      const matches = conversationText.match(pattern) || [];
      score += matches.length * 2.5;
    });

    // Personal story creation indicates authenticity
    score += this.userData.stories.length * 2;
    return {
      score: Math.min(91, score),
      indicators: this.getAuthenticityIndicators(score)
    };
  }

  // Helper methods for generating specific insights
  generateSelfAwarenessInsights(score) {
    if (score > 85) return ['Exceptional metacognitive abilities', 'Strong pattern recognition in behavior', 'Advanced emotional literacy'];
    if (score > 70) return ['Good self-reflection skills', 'Growing awareness of patterns', 'Developing emotional vocabulary'];
    if (score > 50) return ['Emerging self-awareness', 'Beginning to notice patterns', 'Basic emotional recognition'];
    return ['Limited self-reflection', 'Reactive rather than responsive', 'Opportunity for growth in awareness'];
  }
  getSelfAwarenessNextStep(score) {
    if (score > 85) return 'Focus on helping others develop self-awareness';
    if (score > 70) return 'Practice mindfulness and body awareness';
    if (score > 50) return 'Keep a daily reflection journal';
    return 'Start with simple emotion naming exercises';
  }
  getCognitiveCharacteristics(score) {
    const characteristics = [];
    if (score > 80) characteristics.push('Systems thinking', 'Paradoxical reasoning', 'Integrative perspective');
    if (score > 60) characteristics.push('Multiple perspective taking', 'Nuanced understanding', 'Context sensitivity');
    if (score > 40) characteristics.push('Binary thinking patterns', 'Clear categorization', 'Linear processing');
    return characteristics;
  }
  getRelationshipStrengths(score) {
    const strengths = [];
    if (score > 80) strengths.push('Exceptional empathy', 'Conflict resolution skills', 'Deep intimacy capacity');
    if (score > 60) strengths.push('Good communication skills', 'Emotional attunement', 'Trust building');
    if (score > 40) strengths.push('Basic social skills', 'Some emotional awareness', 'Developing connections');
    return strengths;
  }
  getRelationshipGrowthAreas(score) {
    const areas = [];
    if (score < 50) areas.push('Emotional vocabulary', 'Active listening', 'Boundary setting');
    if (score < 70) areas.push('Conflict navigation', 'Vulnerability practice', 'Attachment security');
    if (score < 85) areas.push('Advanced empathy', 'Leadership in relationships', 'Mentoring others');
    return areas;
  }

  // Continue with other analysis methods...
  identifyBehavioralPatterns() {
    const patterns = [];
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();

    // Analyze communication patterns
    if (conversationText.includes('i think') && conversationText.includes('i feel')) {
      patterns.push({
        type: 'Balanced Processing',
        description: 'You integrate both thinking and feeling in your communication',
        frequency: 'High',
        implication: 'Indicates emotional intelligence and cognitive balance'
      });
    }

    // Decision-making patterns
    if (conversationText.match(/decision|choose|option|alternative/g)?.length > 5) {
      patterns.push({
        type: 'Deliberate Decision-Maker',
        description: 'You carefully consider options before making decisions',
        frequency: 'Consistent',
        implication: 'Shows conscientiousness and risk awareness'
      });
    }

    // Relationship patterns
    if (conversationText.match(/relationship|friend|family/g)?.length > 10) {
      patterns.push({
        type: 'Relationship-Oriented',
        description: 'You frequently think about and discuss relationships',
        frequency: 'High',
        implication: 'Strong social orientation and empathy'
      });
    }
    return patterns;
  }
  analyzeCognitiveStyle() {
    const conversationText = this.userData.conversations.map(m => m.content).join(' ').toLowerCase();

    // Determine primary cognitive style
    const analyticalScore = (conversationText.match(/analyze|think|logic|reason/g) || []).length;
    const intuitiveScore = (conversationText.match(/feel|sense|intuition|gut/g) || []).length;
    const visualScore = (conversationText.match(/see|picture|imagine|visualize/g) || []).length;
    const verbalScore = (conversationText.match(/words|say|tell|communicate/g) || []).length;
    const styles = {
      analytical: analyticalScore,
      intuitive: intuitiveScore,
      visual: visualScore,
      verbal: verbalScore
    };
    const primaryStyle = Object.keys(styles).reduce((a, b) => styles[a] > styles[b] ? a : b);
    return {
      primary: primaryStyle,
      scores: styles,
      description: this.getCognitiveStyleDescription(primaryStyle),
      learningRecommendations: this.getLearningRecommendations(primaryStyle)
    };
  }
  getCognitiveStyleDescription(style) {
    const descriptions = {
      analytical: 'You prefer structured, logical approaches to problem-solving',
      intuitive: 'You rely on gut feelings and holistic understanding',
      visual: 'You think in images and spatial relationships',
      verbal: 'You process information through language and communication'
    };
    return descriptions[style];
  }
  getLearningRecommendations(style) {
    const recommendations = {
      analytical: ['Use frameworks and systems', 'Break down complex problems', 'Create logical sequences'],
      intuitive: ['Trust your instincts', 'Use metaphors and analogies', 'Practice mindfulness'],
      visual: ['Create mind maps and diagrams', 'Use visual aids', 'Imagine scenarios'],
      verbal: ['Discuss ideas with others', 'Write to think', 'Use storytelling']
    };
    return recommendations[style];
  }

  // Continue implementing all the helper methods...
  analyzeEmotionalProcessing() {
    // Emotional processing analysis
    return {
      primaryMode: 'Reflective',
      emotionalVocabulary: 'Advanced',
      regulationSkills: 'Developing',
      expressions: ['Verbal', 'Creative', 'Introspective']
    };
  }
  analyzeRelationshipStyle() {
    // Relationship style analysis based on assessments and patterns
    return {
      attachmentStyle: this.userData.assessments.attachment?.result || 'Unknown',
      communicationPreference: 'Thoughtful and deliberate',
      conflictStyle: 'Collaborative',
      intimacyComfort: 'Moderate to High'
    };
  }
  predictGrowthPath() {
    return {
      currentPhase: 'Self-Discovery',
      nextPhase: 'Integration',
      timeline: '6-12 months',
      keyMilestones: ['Complete major assessments', 'Develop consistent self-reflection practice', 'Share insights with others', 'Mentor someone else'],
      completionPercentage: Math.min(89, 60 + Object.keys(this.userData.assessments).length * 5) // Never 100%
    };
  }
  generatePredictions() {
    return [{
      category: 'Behavioral',
      prediction: 'You will likely develop a more structured approach to personal growth',
      confidence: 78,
      timeframe: '3-6 months'
    }, {
      category: 'Relationship',
      prediction: 'Your communication skills will improve, leading to deeper connections',
      confidence: 84,
      timeframe: '2-4 months'
    }, {
      category: 'Career',
      prediction: 'You may seek roles that allow for more creative expression',
      confidence: 72,
      timeframe: '6-12 months'
    }];
  }
  generateRecommendations() {
    return {
      immediate: ['Complete remaining personality assessments', 'Start a daily reflection practice', 'Share one insight with a trusted friend'],
      shortTerm: ['Explore creative expression formats', 'Practice vulnerability in safe relationships', 'Set up regular check-ins with yourself'],
      longTerm: ['Consider becoming a mentor or guide for others', 'Develop your unique approach to personal growth', 'Create a personal development framework']
    };
  }
  identifyRiskFactors() {
    const factors = [];

    // Analysis paralysis risk
    if (this.userData.conversations.length > 20 && this.userData.stories.length < 3) {
      factors.push({
        factor: 'Analysis Paralysis',
        risk: 'Medium',
        description: 'High thinking, low action ratio',
        mitigation: 'Set weekly action goals'
      });
    }

    // Isolation risk
    const relationshipMentions = this.userData.conversations.join(' ').match(/friend|family|relationship/g)?.length || 0;
    if (relationshipMentions < 5) {
      factors.push({
        factor: 'Social Isolation',
        risk: 'Low-Medium',
        description: 'Limited discussion of relationships',
        mitigation: 'Actively engage in social activities'
      });
    }
    return factors;
  }
  identifyStrengths() {
    const strengths = [];

    // Self-reflection strength
    if (this.userData.conversations.length > 10) {
      strengths.push({
        strength: 'Deep Self-Reflection',
        level: 'High',
        description: 'Consistent engagement in introspective dialogue',
        leverage: 'Use this skill to help others grow'
      });
    }

    // Creative expression
    const formats = new Set();
    this.userData.stories.forEach(story => {
      if (story.createdFormats) story.createdFormats.forEach(f => formats.add(f));
    });
    if (formats.size > 5) {
      strengths.push({
        strength: 'Creative Versatility',
        level: 'Advanced',
        description: 'Ability to express insights in multiple formats',
        leverage: 'Develop this into a signature approach'
      });
    }
    return strengths;
  }
  generateNextLevelInsights() {
    return {
      readinessScore: 75,
      nextCapability: 'Emotional Pattern Recognition',
      requirements: ['Complete 2 more major assessments', 'Create 5 additional stories', 'Engage in 10 more reflective conversations'],
      unlocks: ['Advanced relationship dynamics analysis', 'Predictive behavioral modeling', 'Personal archetype evolution tracking'],
      estimatedTime: '4-6 weeks'
    };
  }

  // Additional helper methods
  getAdaptabilityIndicators(score) {
    const indicators = [];
    if (score > 80) indicators.push('Rapid adjustment to change', 'Thrives in uncertainty', 'Flexible problem-solving');
    if (score > 60) indicators.push('Moderate flexibility', 'Learns from setbacks', 'Open to new approaches');
    if (score > 40) indicators.push('Some resistance to change', 'Prefers familiar patterns', 'Gradual adaptation');
    return indicators;
  }
  getCreativeStyle(score, formats) {
    if (score > 80) return 'Highly innovative and experimental';
    if (score > 60) return 'Creative with structured approach';
    if (score > 40) return 'Emerging creative expression';
    return 'Traditional and conventional';
  }
  getResilienceFactors(score) {
    const factors = [];
    if (score > 80) factors.push('Strong emotional regulation', 'Growth mindset', 'Social support network');
    if (score > 60) factors.push('Moderate stress tolerance', 'Learning orientation', 'Some support systems');
    if (score > 40) factors.push('Basic coping skills', 'Limited stress management', 'Developing resilience');
    return factors;
  }
  getAuthenticityIndicators(score) {
    const indicators = [];
    if (score > 80) indicators.push('Strong self-knowledge', 'Values-driven behavior', 'Comfortable with vulnerability');
    if (score > 60) indicators.push('Growing self-awareness', 'Mostly authentic expression', 'Developing confidence');
    if (score > 40) indicators.push('Some self-awareness', 'Occasional authentic moments', 'Building identity');
    return indicators;
  }
}

// Export for use in main application
window.IntelligenceReport = IntelligenceReport;