/**
 * 直接调用 getSkillDirCommands 验证 skill 是否被正确加载。
 * 不需要 LLM API key。
 *
 * 运行: cd claude-code-backend && bun run tests/verify_skills_loaded.ts
 */

// Set git bash path before importing anything
process.env.CLAUDE_CODE_GIT_BASH_PATH = 'D:\\Software\\Git\\bin\\bash.exe'

import { getSkillDirCommands } from '../src/skills/loadSkillsDir.js'

const cwd = 'D:\\Document\\Study\\experiment\\skill-eval'

async function main() {
  console.log(`Testing skill loading from cwd: ${cwd}`)
  console.log(`Expected skills dir: ${cwd}\\.claude\\skills\\`)
  console.log('')

  try {
    const commands = await getSkillDirCommands(cwd)
    console.log(`Loaded ${commands.length} skill(s):`)
    console.log('')

    for (const cmd of commands) {
      console.log(`  /${cmd.name}`)
      console.log(`    description: ${cmd.description}`)
      console.log(`    userInvocable: ${cmd.userInvocable}`)
      console.log(`    contentLength: ${cmd.contentLength}`)
      console.log('')
    }

    const expectedSkills = [
      'career_direction_exploration',
      'role_cognition_analysis',
      'target_role_positioning',
      'career_path_simulation',
      'industry_opportunity_analysis',
    ]

    const loadedNames = commands.map(c => c.name)
    const found = expectedSkills.filter(s => loadedNames.includes(s))
    const missing = expectedSkills.filter(s => !loadedNames.includes(s))

    console.log('---')
    console.log(`Found ${found.length}/${expectedSkills.length} expected skills`)
    if (missing.length > 0) {
      console.log(`Missing: ${missing.join(', ')}`)
    }

    if (found.length === expectedSkills.length) {
      console.log('\n[PASS] All skills loaded successfully!')
      process.exit(0)
    } else if (found.length > 0) {
      console.log('\n[PARTIAL] Some skills loaded')
      process.exit(0)
    } else {
      console.log('\n[FAIL] No expected skills found')
      process.exit(1)
    }
  } catch (err) {
    console.error('[ERROR]', err)
    process.exit(1)
  }
}

main()
