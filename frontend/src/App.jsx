import { ActivityIndicator, Pressable, ScrollView, Text, View } from "react-native";

import { DEFAULT_SCALE } from "./dashboard/lib/constants";
import { useDashboardData } from "./dashboard/hooks/useDashboardData";
import { useRouteState } from "./dashboard/hooks/useRouteState";
import styles from "./dashboard/styles";
import OverviewView from "./dashboard/views/OverviewView";
import PlayerView from "./dashboard/views/PlayerView";

import { useState } from "react";

export default function App() {
  const [scale, setScale] = useState(DEFAULT_SCALE);
  const { route, navigateOverview, navigatePlayer } = useRouteState();
  const { error, loading, overviewData, playerData, reload } = useDashboardData(route, scale);

  return (
    <View style={styles.root}>
      <View style={[styles.blob, styles.blobA]} />
      <View style={[styles.blob, styles.blobB]} />
      <View style={[styles.blob, styles.blobC]} />

      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.shell}>
          {loading ? (
            <View style={styles.stateBox}>
              <ActivityIndicator size="large" color="#6ee9f8" />
              <Text style={styles.stateText}>Chargement des stats depuis la DB...</Text>
            </View>
          ) : null}

          {!loading && error ? (
            <View style={styles.stateBox}>
              <Text style={styles.errorTitle}>Erreur dashboard</Text>
              <Text style={styles.stateText}>{error}</Text>
              <Pressable onPress={reload} style={styles.retryButton}>
                <Text style={styles.retryButtonText}>Réessayer</Text>
              </Pressable>
            </View>
          ) : null}

          {!loading && !error && route.view === "overview" && overviewData ? (
            <OverviewView
              data={overviewData}
              scale={scale}
              onScaleChange={setScale}
              onOpenPlayer={navigatePlayer}
            />
          ) : null}

          {!loading && !error && route.view === "player" && playerData ? (
            <PlayerView
              data={playerData}
              scale={scale}
              onScaleChange={setScale}
              onBack={navigateOverview}
            />
          ) : null}
        </View>
      </ScrollView>
    </View>
  );
}
