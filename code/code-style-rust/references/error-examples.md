# 오류·로그 예

## thiserror

```rust
#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("config file not found: {path}")]
    NotFound { path: PathBuf },
    #[error("failed to parse config")]
    Parse(#[from] toml::de::Error),
}
```

## anyhow

```rust
use anyhow::Context;

fn main() -> anyhow::Result<()> {
    let config = Config::load(&path)
        .with_context(|| format!("failed to load config: {}", path.display()))?;
    anyhow::ensure!(config.is_valid(), "config should be valid");
    Ok(())
}
```

## tracing

```rust
use tracing::{debug, info, instrument};

#[instrument(skip(self), fields(session_id = %self.id))]
fn run(&self) -> Result<(), EngineError> {
    info!("session started");
    debug!(turn = self.turn, "sending prompt");
    Ok(())
}
```

## tracing-subscriber

```rust
tracing_subscriber::fmt()
    .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
    .with_writer(std::io::stderr)
    .init();
```
