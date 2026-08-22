require_relative "../lib/boukensha"

ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../../.boukensha", __dir__)

config = Boukensha::Config.new
player_settings = config.tasks(:player)
system_prompt = Boukensha::Tasks::Player.system_prompt(
  player_settings,
  user_prompts_dir: config.user_prompts_dir
)

ctx = Boukensha::Context.new(
  task: Boukensha::Tasks::Player,
  system: system_prompt
)

registry = Boukensha::Registry.new(ctx)

registry.tool("move",
  description: "Move the player in a direction (north, south, east, west, up, down)",
  parameters: { direction: { type: "string" } }
) do |direction:|
  "You move #{direction} into a torch-lit corridor."
end

registry.tool("shout",
  description: "Shout a message so everyone in the zone can hear it",
  parameters: { message: { type: "string" } }
) do |message:|
  message.upcase
end

puts "=== BOUKENSHA Step 2: Tool Registry ==="
puts
puts "Config:  #{config}"
puts "Context: #{ctx}"
puts "Tools:"
ctx.tools.each_value { |t| puts "  #{t}" }
puts

puts "Dispatching 'shout' with message='dragon spotted'..."
result = registry.dispatch("shout", { "message" => "dragon spotted" })
puts "Result: #{result}"
puts

puts "Dispatching 'move' with direction='north'..."
result = registry.dispatch("move", { "direction" => "north" })
puts "Result: #{result}"
puts

begin
  registry.dispatch("flee")
rescue Boukensha::UnknownToolError => e
  puts "UnknownToolError caught: #{e.message}"
end
